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


def OnlyNewer(
    get_identifier_func,
    get_elements_func=None,
    build_partial_response=None):
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):

            def find(needle, seq):
                for ii, elm in enumerate(seq):
                    if elm == needle:
                        return ii, elm
                    return len(seq)

            if "If-Range" in request.META:
                newest_id = request.META["If-Range"]

                # If we dont' override the way we handle responses
                # assume they're the normal json responses with data
                # as one of the top elements, there is a weird scoping
                # issue that occurs here which is why we shuffle variables
                # around like this.
                get_elements = get_elements_func
                if get_elements_func == None:
                    get_elements = lambda resp: json.loads(resp)["data"]
                    
                build_partial = build_partial_response
                if not build_partial_response:
                    build_partial = lambda elements: api_out(elements)

                response = fn(self, request, *args, **kwargs)
                elements = get_elements(response)
                elements = elements[:find(newest_id, get_identifier_func)]
                return build_partial(elements)
            else:
                return fn(self, request, *args, **kwargs)
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

