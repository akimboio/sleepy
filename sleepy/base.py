"""
Sleepy

A RESTful api framework built on top of Django that simplifies common RESTful
idioms. Originally created at akimbo.

:author: Adam Haney
:contact: adam.haney@akimbo.io
:license: (c) 2013 Akimbo
"""

__author__ = "Adam Haney"
__license__ = "Copyright (c) 2013 Akimbo"

HTTP_READ_ONLY_METHODS = ['GET', 'HEAD', 'OPTIONS']
HTTP_METHODS = HTTP_READ_ONLY_METHODS + ['POST', 'PUT', 'DELETE']

import django.http

from django.conf import settings

from responses import api_error

XS_SHARING_ALLOWED_ORIGINS = getattr(
    settings,
    'XS_SHARING_ALLOWED_ORIGINS',
    ['*']
)

XS_SHARING_ALLOWED_METHODS = getattr(
    settings,
    'XS_SHARING_ALLOWED_METHODS',
    ['GET', 'POST', 'PUT', 'DELETE']
)

XS_SHARING_ALLOWED_HEADERS = getattr(
    settings,
    'XS_SHARING_ALLOWED_HEADERS',
    ['Content-type', 'Authorization']
)

class Base:
    """
    The base method all http handlers will inherit from. This functor
    like object handles the scaffolding of __call__ requests to make
    sure if a GET, POST, PUT or DELETE request is made that it is
    routed to the appropriate method in a child class or an error is
    thrown. It also provides the functions used to output django
    responses in json format.
    """

    def __init__(self):
        try:
            self.read_only = settings.SLEEPY_READ_ONLY
        except AttributeError:
            self.read_only = False

    def _origin_is_allowed(self, origin):
        """
        This helper method validates the url given to us in an 'Origin:'
        request header.
        """
        if ('*' in XS_SHARING_ALLOWED_ORIGINS or
                origin in XS_SHARING_ALLOWED_ORIGINS):
            return True

        return False

    def __call__(self, request, *args, **kwargs):
        # Check if we're in read only mode
        if (self.read_only == True
            and request.method not in HTTP_READ_ONLY_METHODS):
            return api_error("the API is in read only mode for maintenance")

        if request.method == "PUT":
            query_dict = django.http.QueryDict(request.body)
            request.PUT = {
                k: v
                for k, v
                in query_dict.items()}
            kwargs.update(request.PUT)

        # Addd requests to kwargs
        kwargs.update(request.REQUEST)

        # Build our response object
        response = django.http.HttpResponse()

        # See if we have an 'Origin:' header in the request. If so, this is
        # a CORS (cross-orgin resource sharing) "preflight" request.
        # See http://enable-cors.org/
        origin_is_allowed = False
        if 'HTTP_ORIGIN' in request.META:

            # Make sure the given origin is allowed
            if not self._origin_is_allowed(request.META['HTTP_ORIGIN']):
                # If the origin is not allowed to make the request then we
                # return an empty 200 response. This will make the cross
                # origin request fail on the client side.
                return response

            origin_is_allowed = True

        # Use introspection to handle OPTIONS requests
        if request.method == 'OPTIONS':

            response['Access-Control-Allow-Origin'] = (
                request.META['HTTP_ORIGIN']
            )

            response['Access-Control-Allow-Methods'] = (
                ",".join(XS_SHARING_ALLOWED_METHODS)
            )

            response['Access-Control-Allow-Headers'] = (
                ",".join(XS_SHARING_ALLOWED_HEADERS)
            )

            return response

        if hasattr(self, request.method):
            response = getattr(self, request.method)(request, *args, **kwargs)

        # Use introspection to handle HEAD requests
        elif request.method == 'HEAD' and hasattr(self, 'GET'):
            response = self.GET(request)
            response.content = ""

        else:
            response = api_error(
                "Resource does not support {0} for this method".format(
                    request.method
                )
            )
            response.status_code = 405

        # if supress_error_codes is set make all response codes 200
        if "suppress_response_codes" in request.REQUEST:
            response.status_code = 200

        if origin_is_allowed:
            response['Access-Control-Allow-Origin'] = (
                request.META['HTTP_ORIGIN']
            )

        return response
