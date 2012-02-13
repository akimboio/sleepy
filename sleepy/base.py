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

from django.http import HttpResponse, HttpResponseRedirect
from django.utils.encoding import iri_to_uri
from collections import OrderedDict
import json
import pycassa
import sys
import traceback
import copy
import sleepy.helpers


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
        pass

    def _call_wrapper(self, request, *args, **kwargs):
        """
        A child class will implement the GET, PUT, POST and DELETE methods
        This simply handles routing for the request types and in the case
        of HEAD requests suppliments implemented GET requests
        """
        self.kwargs = kwargs
        self.request = request

        self._pre_call_wrapper(request, *args, **kwargs)

        if hasattr(self, request.method):
            result = getattr(self, request.method)(request, *args, **kwargs)

        elif request.method == 'HEAD'and hasattr(self, 'GET'):
            get_result = self.GET(request)
            for k, v in get_result:
                result[k] = get_result[k]
        else:
            result.status_code = 405
            result = self.json_err(
                "Resource does not support {0} for this method".format(
                    request.method))

        # if supress_error_codes is set make all response codes 200
        if "suppress_response_codes" in request.REQUEST:
            result.status_code = 200

        return result

    def _pre_call_wrapper(self, request, *args, **kwargs):
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
        cp = copy.deepcopy(self)
        return cp._call_wrapper(request, *args, **kwargs)

    def json_err(
        self,
        error,
        error_type="Error",
        error_code=400,
        meta_data=None,
        headers=None):
        """
        Takes a string which describes the error that occured and returns a
        django object containing a json_encoded error message

        :Parameters:
        error : string
          a string describing the error that occured
        error_type : string
          the 'class' of the error 'Parameter Error', 'Authentication Error'
          this is useful of you would like to provide a small number of
          error types that clients might deal with in different ways.
        error_code : string
          the http response code that will be passed, default is 400
        meta_data : dictionary
          A dictionary of elements that will be placed on the same level
          as the 'error' key. This is helpful if you would like to
          provide some sort of additional information to the user about the
          error that doesn't make sense inside of the error tag.
          The api version would be an example of something that might
          go here.
        headers : dictionary
          A dictionary of header information. The key will be the header
          type and the value will be the value of the header.
        """

        api_response = HttpResponse(mimetype='application/json')

        # Set meta_data to an empty dictionary if it's None
        if None == meta_data:
            meta_data = {}

        # Set headers to an empty dictionary if it's None
        if None == headers:
            headers = {}

        # Format the error response into our common format
        response = {'error': {'message': error, 'type': error_type}}

        if len(meta_data) > 0:
            response.update(meta_data)

        # Dump out a JSON representation of the responsde
        return_string = json.dumps(response)

        # Handle JSONP
        if "callback" in self.request.REQUEST:
            api_response = HttpResponse(mimetype='text/javascript')
            return_string = "%s(%s)" % (self.request.REQUEST["callback"],
                                        return_string)

        # Set the value of the response
        api_response.write(return_string)

        # set the response code
        api_response.status_code = error_code

        # Set headers
        for k, v in headers.items():
            api_response[k] = v

        return api_response

    def json_out(
        self,
        data,
        meta_data=None,
        cgi_escape=True,
        indent=None,
        status_code=200,
        headers=None):
        """
        json_out takes a python datastructure (list, dict,
        OrderedDict, etc) as an argument and returns a django response
        containing a json encoded string of the data structure.

        :Parameters:
          data: mixed
            A data structure (typically a list, dict or OrderedDict)
            to output as JSON
          meta_data : mixed
            An additional data structure at the same level as data
            that would be used to display information that isn't
            'data'
          cgi_escape : boolean
            Whether or not to cgi escape the resulting
            response object
          indent : boolean
            The ammount of whitespace to indent for each level of json
          status_code : integer
            The HTTP response code to pass back for the response
          headers : dictionary
            A dictionary representing the response headers we would
            like to send back for this request
        """

        api_response = HttpResponse(mimetype='application/json')

        if None == meta_data:
            meta_data = {}

        if None == headers:
            headers = {}

        response = {'data': data}
        response.update(meta_data)

        if "debug" in self.request.REQUEST:
            indent = 2

        json_string = json.dumps(response, indent=indent)

        if "callback" in self.request.REQUEST:
            api_response = HttpResponse(mimetype='text/javascript')
            json_string = "{0}({1})".format(
                self.request.REQUEST["callback"],
                json_string)

        api_response.write(json_string)

        api_response.status_code = status_code

        for k, v in headers.items():
            api_response[k] = v

        return api_response

    def blob_out(self, data, content_type, headers=None):
        """
        blob_out takes a bytestring with blob content
        and a content_type and returns the blob
        object as an HttpResponse

        :Parameters:
          data : string
            A byte string of the binary data we wish to output
          content_type : string
            A string describing the MIME type of the binary object
          headers : dictionary
            A dictionary representing the headers we would like to
            use for the response
        """

        if None == headers:
            headers = {}

        api_response = HttpResponse(
            data,
            mimetype=content_type,
            content_type=content_type)

        api_response["Pragma"] = "no-cache"
        api_response["Cache-Control"] = "no-cache"
        api_response["Content-Length"] = len(data)

        for k, v in headers.items():
            api_response[k] = v

        return response

    def redirect_out(
        self,
        url,
        meta_info=None,
        url_key_name="url",
        status_code=302,
        headers=None):
        """
        Outputs an HTTP 302 redirect response to a given url with
        optional contents. This can be handy so if we want to redirect
        a user to a given url but the programmer wants to get the
        redirect url as a string they can take advantage of the
        suppress_response_codes parameter and get a datastructure
        with a url.

        :Paramters:
          url : string
            The url we wish to redirect to.
          meta_info : mixed
            A datastructure for meta data that will be passed back
          url_key_name : string
            This is included only for backwards compatibility on
            some of retickr's apis. In general unless you have a
            good reason the key name for the url string that
            is passed back will be url, but if you MUST change
            it you may do so here.
          status_code : integer
            Allows us ot override the response code for this method.
            301 and 302 are valid response codes for a redirect but
            if you shove something else in this method won't complain
            NOTE: if the requst passes suppress_response_codes this
            parameter will be ignored
        """
        if None == headers:
            headers = {}

        api_response = HttpResponse(mimetype='application/json')
        api_response['Location'] = iri_to_uri(url)
        api_response.status_code = status_code

        if not meta_info:
            meta_info = {}

        response = {"data": {url_key_name: url}}
        response.update(meta_info)

        api_response.write(json.dumps(response))

        for k, v in headers.items():
            api_response[k] = v

        return api_response


class BaseServerError(Base):
    def __format_traceback(self, traceback):
        html_string = ""
        for k in traceback.keys():
            html_string += "<h2>{0}</h2>\n<ul>".format(k)
            for elm in traceback[k]:
                html_string += "<li>{0}</li>".format(elm)
            html_string += "</ul>"
        return html_string

    def _call_wrapper(self, request):
        self.response = HttpResponse(mimetype='application/json')
        self.kwargs = kwargs
        self.request = request

        # Build traceback object
        tb = [sys.exc_info()[0].__name__ + " " + str(sys.exc_info()[1])]
        for elm in traceback.extract_tb(sys.exc_info()[2]):
            tb.append(elm[0] + " in "
                      + elm[2] + ": "
                      + str(elm[1])
                      + ". " + str(elm[3]))
        trace = OrderedDict()
        trace['uri'] = [request.path]
        trace['traceback'] = tb
        trace['get'] = {
            str(k): str(request.GET[k])
            for k in request.GET
            }
        trace['post'] = {
            str(k): str(request.GET[k])
            for k in request.POST
            }
        trace['files'] = request.FILES.keys()
        trace['globals'] = {str(k): str(v) for k, v in globals().items()}
        trace['locals'] = {str(k): str(v) for k, v in locals().items()}
        trace['path'] = sys.path

        # If the user passes "chucknorris" then we show them the full trace
        if "chucknorris" in request.REQUEST:
            self.result = self.json_out(
                {'response': trace},
                indent=1,
                status_code=500)

        # Otherwise send an email
        else:
            traceback.print_tb(sys.exc_info()[2])
            sleepy.helpers.send_email(
                    "support@retickr.com",
                    "api@retickr.com",
                    "API Error {0}".format(self.__class__.__name__),
                    self.__format_traceback(trace))

            self.result = self.json_err("An unexpected error occured",
                                        error_code=500)
