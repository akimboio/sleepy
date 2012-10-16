"""
Sleepy Decorators

These decorators implement code 'contracts' which define the context
that decorated functions run in. These are helpful for repetitive
tasks such as tranformation, validation, or authentication.

:author: Adam Haney
:organization: Akimbo
:contact: adam.haney@akimbo.io
:license: Copyright (c) 2011 akimbo, LLC
"""

__author__ = "Adam Haney <adam.haney@akimbo.io>"
__license__ = "Copyright (c) 2011 akimbo, LLC"

import json

from django.utils.decorators import wraps

from sleepy.responses import api_out, api_error
from sleepy.helpers import find


def RequiresParameters(params):
    """
    This is decorator that makes sure the function it wraps has received a
    given parameter in the request.REQUEST object. If the wrapped function
    did not receive this parameter it throws a django response containing
    an error and bails out
    """
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            if set(params) <= set(request.REQUEST):
                return fn(self, request, *args, **kwargs)
            else:
                return api_error(
                    "{0} reqs to {1} should contain the {2} parameter".format(
                        fn.__name__,
                        request.build_absolute_uri(),
                        set(params) - set(request.REQUEST)
                        )
                    )
        return _check
    return _wrap


def RequiresUrlAttribute(param):
    """
    This is a decorator that makes sure that a particular attribute in a url
    pattern has been included for this given calling function. This seems
    like a strange problem because Djanog can map urls matchign regexes
    to specific functions, but in our case in Sleepy we map to
    an object for a regular expressiona and we might be more liberal
    in what we accept for a GET call than a POST cal for example
    there might be two regular expressions that point to an endpoin
    /endpoint and /endpoint/(P.*)<entity> and we might require that
    post refers to a given entitity. This is a convenience decorator for
    doing that which hopefully eliminates the length of methods
    """
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            if param in kwargs:
                return fn(self, request, *args, **kwargs)
            else:
                return api_error(
                    "{0} requests to {1} should contain {2} in the url".format(
                        fn.__name__,
                        request.build_absolute_uri(),
                        param
                        )
                    )
        return _check
    return _wrap


def ParameterAssert(param, func, description):
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            if param in kwargs and not func(kwargs[param]):
                return api_error(
                    "{0} {1}".format(param, description),
                    "Parameter Error"
                    )
            else:
                return fn(self, request, *args, **kwargs)
        return _check
    return _wrap


def ParameterType(**types):
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            for param, type_ in types.items():
                try:
                    kwargs[param] = type_(kwargs[param])

                    if type_ == bool:
                        if kwargs[param].lower() == "true":
                            kwargs[param] = True
                        elif kwargs[param].lower() == "false":
                            kwargs[param] = False
                        else:
                            kwargs[param] = type_(param)

                except KeyError:
                    # If there isn't a parameter to type check we assume
                    # that the default was declared as a default parameter
                    # to the function
                    pass

                except ValueError:
                    return api_error(
                        "{0} parameter must be of type {1}".format(
                            param,
                            type_
                            )
                        )

            return fn(self, request, *args, **kwargs)
        return _check
    return _wrap


def ParameterTransform(param, func):
    def _wrap(fn):
        def _transform(self, request, *args, **kwargs):
            if param in kwargs:
                try:
                    kwargs[param] = func(kwargs[param])
                except:
                    return api_error(
                        "the {0} parameter could not be parsed".format(param),
                        "Parameter Error"
                        )
            return fn(self, request, *args, **kwargs)
        return _transform
    return _wrap


def OnlyNewer(element_key):
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):

            if "If-Range" in request.META:
                newest_id = request.META["If-Range"]
            elif "_if_range" in request.REQUEST:
                newest_id = request.REQUEST["_if_range"]
            else:
                return fn(self, request, *args, **kwargs)

            # Force newest_id to be a string
            newest_id = str(newest_id)

            # Call the underlying function and get the response
            response = fn(self, request, *args, **kwargs)

            # Convert to JSON
            response = json.loads(response.content)

            # Grab the full list of elements out of the response
            if "error" in response:
                return api_error(
                    response["error"]["message"],
                    error_type=response["error"]["type"])

            elements = response["data"]["stories"]

            meta_info = {
                k: v
                for k, v in response.items()
                if k != "data"
                }

            # Get the index of the element which is the "newest"
            # element (newest) is passed in, in the list so we
            # can slice the list and only return elements newer
            # than that
            idx = find(
                newest_id,
                [
                    str(elm[element_key])
                    for elm
                    in elements
                    ]
                )[0]

            return api_out({"stories": elements[:idx]}, meta_info)

        return _check
    return _wrap


def AbsolutePermalink(func, protocol="https://"):
    from django.core.urlresolvers import reverse
    from django.contrib.sites.models import Site

    @wraps(func)
    def inner(*args, **kwargs):
        bits = func(*args, **kwargs)
        path = reverse(bits[0], None, *bits[1:3])
        domain = Site.objects.get_current().domain
        return u"{0}{1}{2}".format(protocol, domain, path)
    return inner

