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

# Universe imports
import json
import urlparse
import copy

# Thirdparty imports
from django.utils.decorators import wraps

# Akimbo imports
from sleepy.responses import api_out, api_error
from sleepy.helpers import value_for_keypath


def RequiresParameters(params):
    """
    This is decorator that makes sure the function it wraps has received a
    given parameter in the request.REQUEST object. If the wrapped function
    did not receive this parameter it throws a django response containing
    an error and bails out
    """
    def _wrap(fn):
        def _requires_parameters_check(self, request, *args, **kwargs):
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
        return _requires_parameters_check
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
        def _requires_url_attribute_check(self, request, *args, **kwargs):
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
        return _requires_url_attribute_check
    return _wrap


def ParameterAssert(param, func, description):
    def _wrap(fn):
        def _parameter_assert_check(self, request, *args, **kwargs):
            if param in kwargs and not func(kwargs[param]):
                return api_error(
                    "{0} {1}".format(param, description),
                    "Parameter Error"
                    )
            else:
                return fn(self, request, *args, **kwargs)
        return _parameter_assert_check
    return _wrap


def ParameterType(**types):
    def _wrap(fn):
        def _parameter_type_check(self, request, *args, **kwargs):
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
        return _parameter_type_check
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


def AttachPaginationLinks(
        element_key,
        keypath="data.stories",
        pagination_keypath="data.actions",
        default_num_stories=25,
        default_offset=0):
    def _wrap(fn):
        def _paginate_check(self, request, *args, **kwargs):
            def build_pagination_links(
                    param_dict,
                    ref_time,
                    offset,
                    num_stories,
                    elements_returned):

                def rebuild_query_string(param_dict):
                    """
                    Why not just use urllib.urlencode?
                    Because it urlencodes all parameters,
                    and when those parameters are already
                    encoded, that causes somee problems.
                    """
                    return "&".join([
                        "=".join([str(tuple_[0]), str(tuple_[1])])
                        for tuple_
                        in param_dict.items()
                        ])

                older_params = copy.copy(param_dict)
                newer_params = copy.copy(param_dict)

                # Update some of the params for pagination purposes
                if elements_returned:
                    # We only update the offsets if we actually
                    # returned elements with this call
                    older_params["offset"] = offset + num_stories
                    newer_params["offset"] = max(0, offset - num_stories)

                older_params["num_stories"] = num_stories
                newer_params["num_stories"] = num_stories

                if ref_time:
                    older_params["ref_time"] = ref_time
                    newer_params["ref_time"] = ref_time

                older_params["get_older"] = True
                newer_params["get_older"] = False

                # Build the endpoints
                actions = {
                    'newer': {
                        'endpoint': "{0}?{1}".format(
                            endpoint,
                            rebuild_query_string(newer_params),
                        ),
                        'http_method': 'GET',
                        'name': 'Newer Stories'
                    },
                    'older': {
                        'endpoint': "{0}?{1}".format(
                            endpoint,
                            rebuild_query_string(older_params),
                        ),
                        'http_method': 'GET',
                        'name': 'Older Stories'
                    }
                }

                return actions

            # Decompose the api call into smaller pieces
            parse_result = urlparse.urlparse(
                request.build_absolute_uri())

            # Construct the endpoint we will be using
            # for pagination
            endpoint = "https://{0}{1}".format(
                parse_result.netloc,
                parse_result.path)

            # Extract the parameters
            if len(parse_result.query):
                # Wait a moment, why aren't we just using .split("=")?
                # Because the values may very well be base64 encoded entities
                # which may end in '=' or '=='.  In those cases, splitting on
                # "=" can cause some very hard to find bugs.
                param_pair_list = []

                for param_pair in parse_result.query.split("&"):
                    # Three cases we need to be aware of here
                    # 1) GET_VAR=VAL
                    #       The ideal and expected case.  Easily parsable.
                    # 2) GET_VAR
                    #       no variable provided
                    # 3) GET_VAR_1=VAL& (splitting on '&') will yield ['GET_VAR_1=VAL', '']
                    #       and '' must be handled as a special case
                    if 0 == len(param_pair):
                        # Handle case 3
                        continue

                    try:
                        # Handle case 1
                        equal_idx = param_pair.index("=")

                        param_tuple = (param_pair[:equal_idx], param_pair[equal_idx+1:])
                    except ValueError:
                        # Handle case 2
                        param_tuple = (param_pair, '')

                    param_pair_list.append(param_tuple)

                param_dict = dict(param_pair_list)
            else:
                param_dict = dict()

            # Get the current params
            offset = int(param_dict.get(
                'offset', default_offset))
            num_stories = int(param_dict.get(
                'num_stories', default_num_stories))
            ref_time = param_dict.get(
                'ref_time', None)

            # Call the underlying function and get the response
            response = fn(self, request, *args, **kwargs)

            # Convert to JSON
            response = json.loads(response.content)

            # Grab the full list of elements out of the response
            if "error" in response:
                return api_error(
                    response["error"]["message"],
                    error_type=response["error"]["type"])

            meta_info = {
                k: v
                for k, v in response.items()
                if k != "data"
                }

            # Access the elements being returned
            elements = value_for_keypath(response, keypath)

            if not ref_time:
                # No ref_time was passed in, so instaed
                # we select the newest update_time so that we can paginate
                # properly
                if len(elements) > 0:
                    ref_time = elements[0][element_key]
                else:
                    ref_time = None

            elements_returned = (0 < len(elements))

            response["data"]['actions'] = build_pagination_links(
                param_dict,
                ref_time,
                offset,
                num_stories,
                elements_returned)

            return api_out(response["data"], meta_info)

        return _paginate_check
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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
