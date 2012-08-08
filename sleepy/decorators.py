"""
Sleepy Decorators

Decorators that implement "guards" or functions that wrap around API methods to
handle preconditions before functions are called. For example "in order to call
this method the user should be authenticated", "in order to call this method
you must pass this parameter" etc.

:author: Adam Haney
:organization: Retickr
:contact: adam.haney@retickr.com
:license: Copyright (c) 2011 retickr, LLC
"""

__author__ = "Adam Haney <adam.haney@retickr.com>"
__license__ = "Copyright (c) 2011 retickr, LLC"

# Thirdparty imports
from django.conf import settings

# Retickr imports
import sleepy.helpers

def create_mysql_connection():
    import MySQLdb
    return MySQLdb.connect(
        host=settings.MYSQL["HOST"],
        user=settings.MYSQL["USER"],
        passwd=settings.MYSQL["PASSWORD"],
        db=settings.MYSQL["NAME"])

def RequiresMySQLConnection(fn):
    """
    This decorator opens a mysql connection, does exception handling and on
    success passes the mysql connection to the wrapped function in
    self.mysql_conn
    """
    def _connect(self, request, *args, **kwargs):
        self.mysql_conn = create_mysql_connection()
        return fn(self, request, *args, **kwargs)
    return _connect


def create_cassandra_connection():
    import pycassa
    return pycassa.connect(
        settings.CASSANDRA["keyspace"],
        settings.CASSANDRA["hosts"],
        settings.CASSANDRA["credentials"])

def RequiresCassandraConnection(fn):
    """
    This decorator opens a pycassa connection to Cassandra.
    """
    def _wrap(fn):
        def _connect(self, request, *args, **kwargs):

            if not hasattr(self, "cassandra_connection"):
                self.cassandra_connection = create_cassandra_connection()
            return fn(self, request, *args, **kwargs)
        return _connect
    return _wrap


def RequiresAuthentication(fn):
    import retickrdata.db.users
    """
    Requires Authentication
    This decorator checks Cassandra for the
    users["<username>"]["Authentication"]["PassHash"] value it then compares
    this with the hash provided by the child class of the password that is
    passed in. If this fails, it prints an error, if it succeeds it calls the
    function it is decorating. Since it's already pulled from Cassandra it
    goes ahead and pulls out the user's UserId and stores it in self.user_id
    we can take advantage of this extra information in many member functions.

    Authentication Methods
    ----------------------
    Currently it supports 2 methods of authentication. A user may
    either pass their username as a GET, POST or PUT or DELETE
    variable (or for that matter a variable for any REQUEST type) or
    when the url pattern supports it they may pass their username as
    part of the url. We also support HTTP Basic Authentication as
    discussed in RFC 1945 and the username may be passed this
    way. Passwords can be passed in as REQUEST parameters in plain
    text (always use HTTPS) or we can use HTTP basic auth. Please note
    that in cases where ther username is passed in in multiple ways
    the usernames must match.
    """
    def _check(self, request, *args, **kwargs):
        header_username = None
        user_password = ""

        # Get ther user_passhash, either from HTTP basic Authorization
        # or hash it from a password
        if "password" in request.REQUEST:
            user_password = request.REQUEST["password"]

        # Using Basic Auth
        elif "HTTP_AUTHORIZATION" in request.META:
            # Attempt to parse the Authorization header
            try:
                header_username, user_password = sleepy.helpers.decode_http_basic(
                    request.META["HTTP_AUTHORIZATION"])
            except ValueError, e:
                return self.json_out(e, "Parameter Error")

        # Pass thru for testing
        elif "HTTP_X_RETICKR_SUDO" in request.META:
            user_password = ""

        else:
            return self.json_err(
                "You must provide a password or use HTTP Basic Auth",
                'Authentication Error',
                error_code=401,
                headers={
                    "WWW-Authenticate": "Basic realm=\"Retickr My News API\""
                    }
                )

        self.user_password = user_password

        # Get username there are several ways they could pass this information
        self.username = None

        if "username" in self.kwargs:
            self.username = self.kwargs["username"]

        elif "username" in request.REQUEST:
            self.username = str(request.REQUEST["username"])

        elif None != header_username:
            self.username = header_username

        else:
            return self.json_err(
                'You must provide a username parameter',
                'Authentication Error',
                error_code=401)

        # If we've passed the username in two places make sure that they match
        if header_username != None and self.username != header_username:
            return self.json_err(
                "the user in the HTTP Authorization header and user"
                + " parameter don't match",
                "Parameter Error",
                error_code=401,
                headers={
                    "WWW-Authenticate": "Basic realm\"Retickr My News API\""
                    }
                )

        # Make sure we're connected to Cassandra
        if not hasattr(self, "cassandra_connection"):
            self.cassandra_connection = pycassa.connect(
                settings.CASSANDRA["keyspace"],
                settings.CASSANDRA["hosts"],
                settings.CASSANDRA["credentials"])

        user_management_obj = retickrdata.db.users.Management(
            self.cassandra_connection)

        try:
            if user_management_obj.authenticate(self.username, user_password):
                return fn(self, request, *args, **kwargs)

            elif request.META.get("HTTP_X_RETICKR_SUDO", "") == settings.SUDO_SECRET:
                return fn(self, request, *args, **kwargs)

            else:
                return self.json_err(
                    "Password Incorrect",
                    "Invalid Password",
                    error_code=401)

        except retickrdata.db.exceptions.UserNotFoundError:
            return self.json_err(
                "This user does not exist",
                "Invalid Username",
                error_code=401
                )

        except retickrdata.db.exceptions.AuthenticationError:

            if request.META.get("HTTP_X_RETICKR_SUDO", "") == settings.SUDO_SECRET:
                return fn(self, request, *args, **kwargs)

            return self.json_err(
                'Password Incorrect',
                'Invalid Password',
                error_code=401)

    return _check


def RequiresParameter(param):
    """
    This is decorator that makes sure the function it wraps has received a
    given parameter in the request.REQUEST object. If the wrapped function
    did not receive this parameter it throws a django response containing
    an error and bails out
    """
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            if param in request.REQUEST:
                return fn(self, request, *args, **kwargs)
            else:
                return self.json_err(
                    "{0} reqs to {1} should contain the {2} parameter".format(
                        fn.__name__,
                        self.__class__.__name__,
                        param
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
            if param in self.kwargs:
                return fn(self, request, *args, **kwargs)
            else:
                return self.json_err(
                    "{0} requests to {1} should contain {2} in the url".format(
                        fn.__name__,
                        self.__class__.__name__,
                        param
                        )
                    )
        return _check
    return _wrap
                        
def ParameterMax(param, max_):
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            if param in self.kwargs and self.kwargs[param] > max_:
                return self.json_err(
                    "{0} has a maximum value of {1}".format(
                        param,
                        max_
                        ),
                    "Parameter Error"
                    )
            # We either didn't pass the parameter or it was
            # in an acceptible range
            else:
                return fn(self, request, *args, **kwargs)
        return _check
    return _wrap
                
                                     
