import os
import re
import json
import base64

import git
from django.http import HttpResponse

from responses import api_out


def str2bool(str_):
    """
    Convert a string representation of a boolean value into
    an actual boolean value.

    >>> str2bool('False')
    False
    >>> str2bool('false')
    False
    >>> str2bool('True')
    True
    >>> str2bool('true')
    True
    """
    str_ = str_.strip().lower()

    if "true" == str_:
        return True
    elif "false" == str_:
        return False

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


def git_version(request, f_):
    if not hasattr(git_version, "version"):
        try:
            repo = git.Repo(os.path.dirname(f_))
            git_version.version = str(repo.commit())
        except:
            git_version.version = "unknown"

    return api_out({"api_sha1": git_version.version})


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
        content_type="application/json",
        status_code=500
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

def find(needle, seq):
    """
    Finds the index of the 'needle' in a sequence,
    if the needle is not found the index is assumed to
    be the length of the sequence.

    >>> find("a", ["a", "b", "c"])
    (0, 'a')
    >>> find("c", ["a", "b", "c"])
    (2, 'c')
    >>> find("d", ["a", "b", "c"])
    (3, None)

    """
    for ii, elm in enumerate(seq):
        if elm == needle:
            return ii, elm
    return len(seq), None


def value_for_keypath(dict, keypath):
    """
    Returns the value of a keypath in a dictionary
    if the keypath exists or None if the keypath
    does not exist.
    
    >>> value_for_keypath({}, '')
    {}
    >>> value_for_keypath({}, 'fake')
    
    >>> value_for_keypath({}, 'fake.path')
    
    >>> value_for_keypath({'fruit': 'apple'}, '')
    {'fruit': 'apple'}
    >>> value_for_keypath({'fruit': 'apple'}, 'fruit')
    'apple'
    >>> value_for_keypath({'fruit': 'apple'}, 'fake')
    
    >>> value_for_keypath({'fruit': 'apple'}, 'fake.path')
    
    >>> value_for_keypath({'fruits': {'apple': 'red', 'banana': 'yellow'}}, '')
    {'fruits': {'apple': 'red', 'banana': 'yellow'}}
    >>> value_for_keypath({'fruits': {'apple': 'red', 'banana': 'yellow'}}, 'fruits')
    {'apple': 'red', 'banana': 'yellow'}
    >>> value_for_keypath({'fruits': {'apple': 'red', 'banana': 'yellow'}}, 'fruits.apple')
    'red'
    >>> value_for_keypath({'fruits': {'apple': {'color': 'red', 'taste': 'good'}}}, 'fruits.apple')
    {'color': 'red', 'taste': 'good'}
    >>> value_for_keypath({'fruits': {'apple': {'color': 'red', 'taste': 'good'}}}, 'fruits.apple.color')
    'red'
    >>> value_for_keypath({'fruits': {'apple': {'color': 'red', 'taste': 'good'}}}, 'fruits.apple.taste')
    'good'
    """
    
    if len(keypath) == 0:
        return dict
    
    keys = keypath.split('.')
    value = dict
    for key in keys:
        if key in value:
            value = value[key]
        else:
            return None
    
    return value


def set_value_for_keypath(dict_, keypath, value, create_if_needed=False):
    """
    Sets the value for a keypath in a dictionary
    if the keypath exists. This modifies the
    original dictionary.
    
    >>> set_value_for_keypath({}, '', None)
    
    >>> set_value_for_keypath({}, '', 'test value')
    
    >>> set_value_for_keypath({'fruit': 'apple'}, '', None)
    
    >>> set_value_for_keypath({'fruit': 'apple'}, '', 'test value')
    
    >>> set_value_for_keypath({'fruit': 'apple'}, 'fruit', None)
    {'fruit': None}
    >>> set_value_for_keypath({'fruit': 'apple'}, 'fruit', 'test value')
    {'fruit': 'test value'}
    >>> set_value_for_keypath({'fruit': 'apple'}, 'fake', None)
    
    >>> set_value_for_keypath({'fruit': 'apple'}, 'fake', 'test value')
    
    >>> set_value_for_keypath({'fruit': {'apple': 'red'}}, 'fruit.apple', 'green')
    {'fruit': {'apple': 'green'}}
    >>> set_value_for_keypath({'fruit': {'apple': 'red'}}, 'fruit.apple', None)
    {'fruit': {'apple': None}}
    >>> set_value_for_keypath({'fruit': {'apple': {'color': 'red'}}}, 'fruit.apple.fake', 'green')
    
    >>> set_value_for_keypath({'fruit': {'apple': {'color': 'red'}}}, 'fruit.apple.color', 'green')
    {'fruit': {'apple': {'color': 'green'}}}
    
    >>> set_value_for_keypath({'fruit': {'apple': {'color': 'red'}}}, 'fruit.apple.color', {'puppies': {'count': 10, 'breed':'boxers'}})
    {'fruit': {'apple': {'color': {'puppies': {'count': 10, 'breed': 'boxers'}}}}}
    
    >>> set_value_for_keypath({'fruit': {'apple': {'color': 'red'}}}, 'fruit.apple.animals', {'puppies': {'count': 10, 'breed':'boxers'}}, create_if_needed=True)
    {'fruit': {'apple': {'color': 'red', 'animals': {'puppies': {'count': 10, 'breed': 'boxers'}}}}}
    
    """
    
    if len(keypath) == 0:
        return None
    
    keys = keypath.split('.')
    if len(keys) > 1:
        key = keys[0]

        if create_if_needed:
            dict_[key] = dict_.get(key, {})

        if key in dict_:
            if set_value_for_keypath(dict_[key], '.'.join(keys[1:]), value,
                create_if_needed=create_if_needed):
                return dict_

        return None
    
    if create_if_needed:
        dict_[keypath] = dict_.get(keypath, {})

    if keypath in dict_:
        dict_[keypath] = value
        return dict_
    else:
        return None
    

if __name__ == "__main__":
    import doctest
    doctest.testmod()

