"""
Sleepy

A RESTful api framework built on top of Django that simplifies common RESTful
idioms. Originally created at retickr.

:author: Adam Haney
:contact: adam.haney@retickr.com
:license: (c) 2011 Retickr
"""

__author__ = "Adam Haney"
__license__ = "Copyright (c) 2011 Retickr"

HTTP_READ_ONLY_METHODS = ['GET', 'HEAD', 'OPTIONS']
HTTP_METHODS = HTTP_READ_ONLY_METHODS + ['POST', 'PUT', 'DELETE']

from django.conf import settings

from responses import api_error


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

        for method in HTTP_METHODS:
            try:
                setattr(self, method, staticmethod(getattr(self, method)))
            except AttributeError:
                pass

    def __call__(self, request, *args, **kwargs):
        """
        Django isn't always thread safe, there are a few ways we can
        get around this problem we can either run on a threaded server
        which can serve requests faster, and to keep ourselves safe we
        can make a deep copy of our api object in memory every
        time. this can lead to high memory loads, but faster
        responses. We can also run on multiple processes with a single
        thread, this can lead to a log jam if a ton of requests come
        in at once if we do opt for the deep copy make sure to include
        maximum-requests (or something similar if you aren't using
        Apache in your conf file. This will help to overcome memory
        leaks. I hate you, mod_wsgi
        """

        # Check if we're in read only mode
        if (self.read_only == True
            and request.method not in HTTP_READ_ONLY_METHODS):
            return api_error("the API is in read only mode for maintenance")

        # Addd requests to kwargs
        kwargs.update(request.REQUEST)

        if hasattr(self, request.method):
            result = getattr(self, request.method)(request, *args, **kwargs)

        # Use introspection to handle HEAD requests
        elif request.method == 'HEAD'and hasattr(self, 'GET'):
            get_result = self.GET(request)
            for k, v in get_result:
                result[k] = get_result[k]

        # Use introspection to handle OPTIONS requests
        elif request.method == 'OPTIONS':
            available_methods = set(HTTP_METHODS) & set(dir(self))
            result["Accept"] = ",".join(available_methods)

        else:
            result = api_error(
                "Resource does not support {0} for this method".format(
                    request.method))
            result.status_code = 405

        # if supress_error_codes is set make all response codes 200
        if "suppress_response_codes" in request.REQUEST:
            result.status_code = 200

        return result
