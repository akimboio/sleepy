"""
Sleepy

A RESTful api framework built on top of Django that simplifies common RESTful
idioms. Originally created at retickr.

:author: Adam Haney
:contact: adam.haney@retickr.com
:license: (c) 2011 Retickr
"""

__author__ = "Adam Haney"
__license__ = "(c) 2011 Retickr"
__conf_file_location__ = "conf.json"

from django.http import HttpResponse, HttpResponseRedirect
from collections import OrderedDict
import json
import pycassa
import sys
import traceback
import copy
import sleepy.helpers

conf = json.load(open(__conf_file_location__))


class Base:
    """
    The base method all http handlers will inherit from. This functor
    like object handles the scaffolding of __call__ requests to make
    sure if a GET, POST, PUT or DELETE request is made that it is
    routed to the appropriate method in a child class or an error is
    thrown. It also makes an initial Cassandra connection and provides
    the functions used to output django responses in json format.
    """
    def __init__(self):
        pass

    def __format_traceback(self, traceback):
        html_string = ""
        for k in traceback.keys():
            html_string += "<h2>{0}</h2>\n<ul>".format(k)
            for elm in traceback[k]:
                html_string += "<li>{0}</li>".format(elm)
            html_string += "</ul>"
        return html_string

    def __call_wrapper(self, request, *args, **kwargs):
        """
        A child class will implement the GET, PUT, POST and DELETE methods
        this method simply creates an initial Cassandra connection (as defined
        by a child class' constructor and does error handling to make sure
        the HTTP request type is suppored by the child class
        """
        self.response = HttpResponse(mimetype='application/json')
        self.kwargs = kwargs
        self.request = request
        self.api_uri = "https://api.retickr.com"

        # Cassandra connection information
        if hasattr(self, 'column_family') and self.column_family != None:
            self.cass_pool = pycassa.connect(
                conf["cassandra"]["keyspace"],
                conf["cassandra"]["hosts"],
                credentials=conf["cassandra"]["credentials"])

            setattr(self, "%s_cf" % self.column_family,
                    pycassa.ColumnFamily(self.cass_pool, self.column_family))
        try:
            if request.method == 'GET' and hasattr(self, 'GET'):
                self.result = self.GET(request)
            elif request.method == 'POST' and hasattr(self, 'POST'):
                self.result = self.POST(request)
            elif request.method == 'PUT' and hasattr(self, 'PUT'):
                self.result = self.PUT(request)
            elif request.method == 'DELETE' and hasattr(self, 'DELETE'):
                self.result = self.DELETE(request)
            else:
                self.response.response_code = 405
                self.result = self.json_err(
                    "Resource does not support {0} for this method".format(
                        request.method))
        except:
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
            trace['get'] = {str(k): str(request.GET[k]) for k in request.GET }
            trace['post'] = {str(k): str(request.GET[k]) for k in request.POST}
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

        return self.result

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
        return cp.__call_wrapper(request, *args, **kwargs)

    def json_err(self,
                 error,
                 error_type="Error",
                 error_code=400,
                 meta_data=None):
        """
        Takes a string which describes the error that occured and returns a
        django object containing a json_encoded error message

        @param error: a string describing the error that occured
        @param error_code: the http response code that will be passed,
            default is 400
        """

        if None == meta_data:
            meta_data = {}

        response = {'error': {'message': error, 'type': error_type}}

        if len(meta_data) > 0:
            response.update(meta_data)

        return_string = json.dumps(response)
        if "callback" in self.request.REQUEST:
            self.response = HttpResponse(mimetype='text/javascript')
            return_string = "%s(%s)" % (self.request.REQUEST["callback"],
                                        return_string)
        self.response.write(return_string)

        if not "suppress_response_codes" in self.request.REQUEST:
            self.response.status_code = error_code

        return self.response

    def json_out(self,
                 data,
                 meta_data=None,
                 cgi_escape=True,
                 indent=None,
                 status_code=200):
        """
        json_out takes a python datastructure (list, dict,
        OrderedDict, etc) as an argument and returns a django response
        containing a json encoded string of the data structure.

        @param data: A data structure (typically a list, dict or OrderedDict)
            to output as JSON
        @param meta_data: An additional data structure at the same
            level as data that would be used to display information
            that isn't 'data'
        @param cgi_escape: Whether or not to cgi escape the resulting
            response object
        """
        if None == meta_data:
            meta_data = {}

        # CGI escape if neccassary
        response = {'data': data}

        # Add meta data if applicable
        if len(meta_data) > 0:
            response.update(meta_data)

        # build JSON string
        if "debug" in self.request.REQUEST:
            indent = 2

        json_string = json.dumps(response, indent=indent)

        if "callback" in self.request.REQUEST:
            self.response = HttpResponse(mimetype='text/javascript')
            json_string = "{0}({1})".format(
                self.request.REQUEST["callback"],
                json_string)

        self.response.write(json_string)
        self.response.status_code = status_code
        return self.response

    def blob_out(self, data, content_type):
        response = HttpResponse(
            data,
            mimetype=content_type,
            content_type=content_type)
        response["Pragma"] = "no-cache"
        response["Cache-Control"] = "no-cache"
        response["Content-Length"] = len(data)
        return response

    def redirect_out(self, url):
        return HttpResponseRedirect(url)
