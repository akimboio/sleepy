"""
Sleepy Decorators

Decorators that implement "guards" or functions that wrap around API methods to
handle preconditions before functions are called. For example "in order to call
this method the user should be authenticated", "in order to call this method
you must pass this parameter" etc.

@author: Adam Haney
@organization: Retickr
@contact: adam.haney@retickr.com
@license: Copyright (c) 2011 retickr, LLC
"""

__author__ = "Adam Haney <adam.haney@retickr.com>"
__license__ = "Copyright (c) 2011 retickr, LLC"
__conf_file_location__ = "./conf.json"

import pycassa
import MySQLdb
import MySQLdb.cursors
import hotshot
import time
import base64
import json

conf = json.load(open(__conf_file_location__))


def RequiresAuthentication(fn):
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

    Currently it supports 3 different methods of
    authentication. A user may either pass their username as a GET, POST or PUT
    or DELETE variable (or for that matter a variable for any REQUEST type) or
    when the url pattern supports it they may pass their username as part of
    the url. We also support HTTP Basic Authentication as discussed in RFC 1945
    and the username may be passed this way. Passwords can be passed in as
    REQUEST parameters in plain text (always use HTTPS), the pass_hash may be
    passed in, or we can use HTTP basic auth. Please note that in cases where
    ther username is passed in in multiple ways the usernames must match.
    """
    def _check(self, request, *args, **kwargs):

        # Get ther user_passhash, either as a parameter, from HTTP basic
        # Authorization or hash it from a password
        self.user_passhash = None
        header_username = None
        if "password" in request.REQUEST:
            self.user_passhash = self.hash(request.REQUEST["password"])
        elif "passhash" in request.REQUEST:
            self.user_passhash = request.REQUEST["passhash"]
        elif "HTTP_AUTHORIZATION" in request.META:
            # Attempt to parse the Authorization header
            try:
                auth_header = request.META['HTTP_AUTHORIZATION']

                # Get the authorization token and base 64 decode it
                auth_string = base64.b64decode(auth_header.split(' ')[1])

                # Grab the username and password from the auth_string
                password = auth_string.split(':')[1]
                header_username = auth_string.split(':')[0]

                self.user_passhash = self.hash(password)

            # The authorization string didn't comply to the standard
            except:
                return self.json_err(
                    "The Authorization header that you passed does not comply"
                    + "with the RFC 1945 HTTP basic authentication standard "
                    + "(http://tools.ietf.org/html/rfc1945) you passed "
                    + "{0}".format(auth_header))

        else:
            return self.json_err(
                "You must provide a password, passhash or use HTTP Basic Auth",
                                 'Authentication Error', error_code=401)

        # Get username there are several ways they could pass this information
        self.username = None
        if "username" in self.kwargs:
            self.username = self.kwargs["username"]
        elif "username" in request.REQUEST:
            self.username = str(request.REQUEST["username"])
        elif None != header_username:
            self.username = header_username
        else:
            return self.json_err('You must provide a username parameter',
                                 'Authentication Error', error_code=401)

        # If we've passed the username in two places make sure that they match
        if header_username != None and self.username != header_username:
            return self.json_err("""You've passed the username in the HTTP """\
                                 """Authorization header and as a parameter"""\
                                 """ they don't match""", "Parameter Error")

        # Make sure we're connected to users_cf
        if not hasattr(self, 'column_family') or self.column_family != 'users':
            setattr(self, "%s_cf" % 'users',
                    pycassa.ColumnFamily(self.cass_pool, 'users'))

        # Get user information
        try:
            user = self.users_cf.get(self.username,
                       read_consistency_level=pycassa.ConsistencyLevel.QUORUM)
        except pycassa.NotFoundException:
            return self.json_err("This user does not exist",
                                 "Invalid Username", error_code=401)

        # Compare hashes
        if user["Authentication"]["PassHash"] != self.user_passhash:
            return self.json_err('Password Incorrect',
                                 'Invalid Password',
                                 error_code=401)

        self.user_id = int(user["Information"]["UserId"])

        # Go ahead and store the user info, it reduces the number
        # of requests to Cassandra
        self.user_info = user

        # Store the last access time for every user so throttling
        # functions can use this info
        self.users_cf.insert(self.username,
                             {"Information":
                                  {"LastApiRequest": str(time.time())}})

        return fn(self, request)
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
                request.REQUEST[param] = unicode(
                    request.REQUEST[param]).encode("utf-8")

                return fn(self, request)
            else:
                return self.json_err("%s requests to %s should"\
                                         " contain the %s paramater"
                                     % (fn.__name__,
                                        self.__class__.__name__, param))
        return _check
    return _wrap


def RequiresMysqlConnection(fn):
    """
    This decorator opens a mysql connection, does exception handling and on
    success passes the mysql connection to the wrapped function in
    self.mysql_conn
    """
    def _connect(self, request, *args, **kwargs):
        self.mysql_conn = MySQLdb.connect(host=conf["mysql"]["host"],
                                          user=conf["mysql"]["user"],
                                          passwd=conf["mysql"]["password"],
                                          db=conf["mysql"]["db"])
        return fn(self, request)
    return _connect


def RequestsPerSecond(reqs):
    """
    This decorator throttles the number of requests a user can make in a second
    This is useful to prevent a ddos from an individual account or IP
    @todo: not working
    """
    def _wrap(fn):
        def _check(self, request, *args, **kwargs):
            # Temporarily Commented out so josh can test
            try:
                if user["Information"]["LastApiRequest"] \
                        > (time.time() - (1000 / reqs)):
                    return self.json_err("Users may only make api"\
                                             " %d requests once a second")
            # We only pass on this error because it's possible the user
            # hasn't been throttled, yet
            except KeyError:
                pass

            return fn(self, request)
        return _check
    return _wrap


def RequiresCassandraConnection(fn):
    def _wrap(fn):
        def _connect(self, request, *args, **kwargs):
            keyspace = conf["cassandra"]["keyspace"]
                                             
            self.cassandra_connection = pycassa.connect(
                keyspace,
                conf["cassandra"]["hosts"],
                credentials=conf["cassandra"]["credentials"])
            return fn(self, request)
        return _connect
    return _wrap


def RequiresCassandraCf(cf, keyspace=None):
    """
    This decorator requests a cassandra connection to a column family. If
    this column family cannot be connected to it bails out and throws a django
    error
    """
    def _wrap(fn):
        def _connect(self, request, *args, **kwargs):
            if None == keyspace:
                try:
                    setattr(self, "%s_cf" % cf,
                            pycassa.ColumnFamily(self.cass_pool, cf))
                except AttributeError:
                    raise AttributeError(
                        "A default Cassandra Keyspace wasn't"\
                            " set in the base class or the pool"\
                            " was unable to connect, the object"\
                            " doesn't have the attribute"\
                            " self.cass_pool")
            else:
                pool = pycassa.connect(keyspace,
                                       conf["cassandra"]["hosts"],
                                       credentials=conf["cassandra"]["credentials"])
                setattr(self, "%s_cf" % cf, pycassa.ColumnFamily(pool, cf))
            return fn(self, request)
        return _connect
    return _wrap


def Profile(logfile):
    def _wrap(fn):
        def _inner(self, request, *args, **kwargs):
            profiler = hotshot.Profile(logfile + "." + \
                                           self.username + "."\
                                           + str(time.time()))
            ret = profiler.runcall(fn, self, request, *args, **kwargs)
            profiler.close()
            return ret
        return _inner
    return _wrap


# Defined Errors
class API_ERRORS:
    PARAMETER_ERROR = "Parameter Error"
    AUTHENTICATION_ERROR = "Authentication Error"
    THIRD_PARTY_ERROR = "Third Party Error"
    OPERATION_NOT_ALLOWED = "Operation Not Allowed"
