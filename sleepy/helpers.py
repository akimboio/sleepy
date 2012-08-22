from django.http import HttpResponse
import re
import json
import base64


def index(request, username=None, *args, **kwargs):
    """
    a convenience function, since no methods support root access this
    is the 'index' for a 'directory' it prints an error stating that
    the root uri is not a supported resource
    """
    return HttpResponse(
        json.dumps(
            {
                'error':
                    {
                    "message": "Nonsupported method for resource",
                    "type": "Not Found Error"
                    },
                }
            ),
        content_type="application/json"
        )


def unexpected_error(request):
    """
    a convenience function that dumps an error message. We can use
    this to conveniently override the server error handler
    to output JSON
    """
    return HttpResponse(
        json.dumps(
            {
                'error': {
                    "message": "An unexpected error occured",
                    "type": "Server Error"
                    }
                }
            ),
        content_type="application/json"
        )


def chunk_split(list, chunk_size):
    """
    Splits a list into N many chunks where N - 1 chunks are of size chunk_size
    and the Nth chunk is the size of the remaining elements in the list
    """
    return [
        list[
            sidx:min(sidx + chunk_size, len(list))]
        for sidx in range(0, len(list), chunk_size)]


def valid_email(email):
    """
    Checks to see if a string is a valid email
    @param email: a string to be validated
    @returns: C{bool}
    """
    email_pattern = ("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\."
                     + "([a-zA-Z]{2,6}|[0-9]{1,3})(\\]?)$")
    if re.match(email_pattern, email) != None:
        return True
    return False


def symbol_encode(
    number,
    symbols="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
    string = ""
    while number != 0:
        number, ii = divmod(number, len(symbols))
        string = symbols[ii] + string
    return string


def decode_http_basic(auth_header):
    try:
        # Get the authorization token and base 64 decode it
        auth_string = base64.b64decode(auth_header.split(' ')[1])

        # Grab the username and password from the auth_string
        password = auth_string.split(':')[1]
        username = auth_string.split(':')[0]

        return username, password

    # The authorization string didn't comply to the standard
    except:
        raise ValueError(
            "The Authorization header that you passed does not comply"
            + "with the RFC 1945 HTTP basic authentication standard "
            + "(http://tools.ietf.org/html/rfc1945) you passed "
            + "{0}".format(auth_header))
