from django.utils.encoding import iri_to_uri
from django.http import HttpResponse
import json


def api_out(
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

    api_response.write(json.dumps(response, indent=indent))

    api_response.status_code = status_code

    for k, v in headers.items():
        api_response[k] = v

    return api_response


def blob_out(data, content_type, headers=None):
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

    api_response["Content-Length"] = len(data)

    for k, v in headers.items():
        api_response[k] = v

    return api_response


def redirect_out(
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


def api_error(
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

    # Set the value of the response
    api_response.write(return_string)

    # set the response code
    api_response.status_code = error_code

    # Set headers
    for k, v in headers.items():
        api_response[k] = v

    return api_response

def robots_disallow(request):
        return HttpResponse("User-agent: *\nDisallow: /", mimetype="text/plain")
