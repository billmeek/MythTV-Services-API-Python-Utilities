# -*- coding: utf-8 -*-

"""API Client."""

from __future__ import print_function
from __future__ import absolute_import
from os import fdopen

import re
import sys
import tempfile
import logging

try:
    import requests
    from requests.auth import HTTPDigestAuth
except ImportError:
    sys.exit('Install python-requests or python3-requests')

from ._version import __version__

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
# If MYTHTV_VERSION_LIST needs to be changed, be sure to     #
# test with the new back/frontend version. If you're just    #
# getting data, no harm will be done. But if you Add/Delete/ #
# Update anything, then all bets are off! Anything requiring #
# an HTTP POST is potentially dangerous.                     #
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #

MYTHTV_VERSION_LIST = ('0.27', '0.28', '29')


def _the_response_is_unexpected(response):
    """
    Really here for readability. Used for Abort/Warning cases
    where a dictionary response means there was a problem and
    a return (with the explanation) should be made.
    """

    return isinstance(response, dict)


class Send(object):
    """Services API."""

    def __init__(self, host, port=6544):
        """
        INPUT:
        ======

        host:     Must be set and is the hostname or IP address of the backend
                  or frontend.

        port:     Only needed if the backend is using a different port
                  (unlikely) or set to 6547 for frontend endpoints. Defaults
                  to 6544.
        """


        self.host = host
        self.port = port
        self.endpoint = None
        self.postdata = None
        self.rest = None
        self.opts = None
        self.session = None
        self.server_version = 'Set to MythTV version after calls to send()'
        self.logger = logging.getLogger(__name__)

        logging.getLogger(__name__).addHandler(logging.NullHandler())

    def send(self, endpoint='', postdata=None, rest='', opts=None):
        """
        Form a URL and send it to the back/frontend. Error handling is done
        here too.

        EXAMPLES:
        =========

        import mythtv_services_api.api as api
        backend = api.Send(host='someName')

        backend.send(endpoint='Myth/GetHostName')

        Returns: {'String': 'someBackend'}

        frontend = api.Send(host='someFrontend', port=6547)
        frontend.send(endpoint='Frontend/GetStatus')

        Returns: {'FrontendStatus': {'AudioTracks':...

        INPUT:
        ======

        endpoint: Must be set. Example: Myth/GetHostName

        postdata: May be set if the endpoint allows it. Used when information
                  is added/changed/deleted. postdata is passed as a Python
                  dict e.g. {'ChanId':1071, ...}. Don't use if rest is used.
                  The HTTP method will be a POST (as opposed to a GET.)

                  If using postdata, TAKE CAUTION!!! Use opts['wrmi']=False
                  1st, turn on DEBUG level logging and then when happy with
                  the data, make wrmi True.

                  N.B. The MythTV Services API is still evolving and the wise
                  user will backup their DB before including postdata.

        rest:     May be set if the endpoint allows it. For example, endpoint=
                  Myth/GetRecordedList, rest='Count=10&StorageGroup=Sports'
                  Don't use if postdata is used. The HTTP method will be a GET.

        opts (Short Description):

        It's OK to call this function without any options set and:

            • If there's postdata, nothing will be sent to the server
            • timeout will be set to 10 seconds
            • It will fail if the backend requires authorization (user/pass
              would be required)

        opts (Details):

        opts is a dictionary of options that may be set in the calling program.
        Default values will be used if callers don't pass all or some of their
        own. The defaults are all False except for 'user', 'pass' and
        'timeout'.

        opts['noetag']:  Don't request the back/frontend to check for matching
                         ETag. Mostly for testing.

        opts['nogzip']:  Don't request the back/frontend to gzip it's response.
                         Useful if watching protocol with a tool that doesn't
                         uncompress it.


        opts['timeout']: May be set, in seconds. Examples: 5, 0.01. Used to
                         prevent script from waiting indefinitely for a reply
                         from the server. Note: a timeout exception is only
                         raised if there are no bytes received from the host on
                         this socket. Long downloads are not affected by this
                         option. Defaults to 10 seconds.

        opts['user']:    Digest authentication. Usually not turned on in the
        opts['pass']:    backend.

        opts['usexml']:  For testing only! If True, causes the backend to send
                         its response in XML rather than JSON. This will force
                         an error when parsing the response. Defaults to False.

        opts['wrmi']:    If True and there is postdata, the URL is then sent to
                         the server.

                         If opts['wrmi'] is False and there is postdata, send
                         NOTHING to the server.

                         This is a fail-safe that allows testing. Users can
                         examine what's about to be sent before doing it (wrmi
                         means: We Really Mean It.)

        opts['wsdl']:    If True return WSDL from the back/frontend. Accepts no
                         rest or postdata. Just set endpoint, e.g. Content/wsdl

        OUTPUT:
        =======

        Either the response from the server in the selected format (default is
        JSON.) Or a dict with keys in one of: 'Abort', 'Warning', 'WSDL', or
        'Image'.

        Callers can handle the response like this:

            backend = api.Send(host=...)
            response = backend.send(...)

            if list(response.keys())[0] in ['Abort', 'Warning']:
                {print|sys.exit}('{}'.format(list(response.values())[0]))

            normal processing...

        If an 'Image' key is returned, then the caller is responsible for
        deleting the temporary filename which is returned in its value e.g.

            {'Image': '/tmp/tmp5pxynqdf.jpeg'}

        However, some errors returned by the server are in XML, e.g. if an
        endpoint is invalid. That will cause the JSON decoder to fail. In
        the application calling this, turn logging on and use the DEBUG
        level. See the next section.

        Whenever send() is used, 'server_version' is set to the value returned
        by the back/frontend in the HTTP Server: header. It is saved as just
        the version, e.g. 0.28. Callers can check it and *may* choose to adjust
        their code work with other versions. See: get_server_version().

        LOGGING:
        ========
        Callers may choose to use the Python logging module. Lines similar to
        the following will make log() statements print if the level is set to
        DEBUG:

            import logging

                logger = logging.getLogger(__name__)
                logging.basicConfig(level=logging.DEBUG
                                    if args['debug'] else logging.INFO)
                logging.getLogger('requests.packages.urllib3')
                                  .setLevel(logging.WARNING)

        """

        self.endpoint = endpoint
        self.postdata = postdata
        self.rest = rest
        self.opts = opts

        self._set_missing_opts()

        url = self._form_url()

        self.logger.debug('URL=%s', url)

        if _the_response_is_unexpected(url):
            return url

        if self.session is None:
            self._create_session()

        if self.postdata:
            pd_response = self._validate_postdata()
            if _the_response_is_unexpected(pd_response):
                return pd_response

        exceptions = (requests.exceptions.HTTPError,
                      requests.exceptions.URLRequired,
                      requests.exceptions.Timeout,
                      requests.exceptions.ConnectionError,
                      requests.exceptions.InvalidURL,
                      KeyboardInterrupt)

        ##############################################################
        # Actually try to get the data and handle errors.            #
        ##############################################################

        try:
            if self.postdata:
                response = self.session.post(url, data=self.postdata,
                                             timeout=self.opts['timeout'])
            else:
                response = self.session.get(url, timeout=self.opts['timeout'])
        except exceptions:
            return {'Abort': 'Connection problem or Keyboard Interrupt, URL={}'
                             .format(url)}

        if response.status_code == 401:
            return {'Abort': 'Unauthorized (401). Need valid user/password.'}

        # TODO: Should handle redirects here (mostly for remote backends.)
        if response.status_code > 299:
            return {'Abort': 'Unexpected status returned: {}: URL was: {}'
                             .format(response.status_code, url)}

        server_header = self._validate_header(response.headers['Server'])

        if _the_response_is_unexpected(server_header):
            return server_header

        try:
            ct_header, image_type = response.headers['Content-Type'].split('/')
        except (KeyError, ValueError):
            ct_header = None

        ##############################################################
        # Finally, return the response in the desired format         #
        ##############################################################

        if self.opts['wsdl']:
            return {'WSDL': response.text}

        if not ct_header:
            try:
                self.logger.debug('1st 60 bytes of response: %s',
                                  response.text[:60])
            except UnicodeEncodeError:
                pass

        if ct_header == 'image':
            handle, filename = tempfile.mkstemp(suffix='.' + image_type)
            self.logger.debug('created %s, remember to delete it.', filename)
            with fdopen(handle, 'wb') as f_obj:
                for chunk in response.iter_content(chunk_size=8192):
                    f_obj.write(chunk)
            return {'Image': filename}

        if self.opts['usexml']:
            return response.text

        try:
            return response.json()
        except ValueError as err:
            return {'Abort': 'Set loglevel=DEBUG to see JSON parsing error: {}'
                             .format(err)}

    def _set_missing_opts(self):
        """
        Sets options not set by the caller to False (or 10 in the
        case of timeout.
        """

        if not isinstance(self.opts, dict):
            self.opts = {}

        for option in ('noetag', 'nogzip', 'usexml', 'wrmi', 'wsdl'):
            try:
                self.opts[option]
            except (KeyError, TypeError):
                self.opts[option] = False

        try:
            self.opts['timeout']
        except KeyError:
            self.opts['timeout'] = 10

        self.logger.debug('opts=%s', self.opts)

        return

    def _form_url(self):
        """Do basic sanity checks and then form the URL."""

        if self.host == '':
            return {'Abort': 'No host name.'}

        if self.endpoint == '':
            return {'Abort': 'No endpoint (e.g. Myth/GetHostName.)'}

        if self.postdata and self.rest:
            return {'Abort': 'Use either postdata or rest.'}

        if self.rest == '' or self.rest is None:
            self.rest = ''
        else:
            self.rest = '?' + self.rest

        return 'http://{}:{}/{}{}'.format(self.host, self.port, self.endpoint,
                                          self.rest)

    def _validate_postdata(self):
        """Return an Abort if the postdata passed doesn't make sense"""

        if self.postdata and not isinstance(self.postdata, dict):
            return {'Abort': 'usage: postdata must be passed as a dict'}

        if self.postdata:
            self.logger.debug('The following postdata was included:')
            for key in self.postdata:
                self.logger.debug('%30s: %s', key, self.postdata[key])

        if self.postdata and not self.opts['wrmi']:
            return {'Warning': 'wrmi=False'}

        if self.opts['wsdl'] and (self.rest or self.postdata):
            return {'Abort': 'usage: rest/postdata aren\'t allowed with WSDL'}

    def _create_session(self):
        """
        Called if a session doesn't already exist. Sets the desired
        headers and provides for authentication.
        """

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Python Services API v{}'
                                                   .format(__version__)})
        if self.opts['noetag']:
            self.session.headers.update({'Cache-Control': 'no-store'})
            self.session.headers.update({'If-None-Match': ''})

        if self.opts['nogzip']:
            self.session.headers.update({'Accept-Encoding': ''})
        else:
            self.session.headers.update({'Accept-Encoding': 'gzip,deflate'})

        if self.opts['usexml']:
            self.session.headers.update({'Accept': ''})
        else:
            self.session.headers.update({'Accept': 'application/json'})

        self.logger.debug('New session')

        # TODO: Problem with the BE not accepting postdata in the initial
        # authorized query, Using a GET first as a workaround. The stack
        # thing is really ugly, must be a better solution.

        try:
            if self.opts['user'] and self.opts['pass']:
                self.session.auth = HTTPDigestAuth(self.opts['user'],
                                                   self.opts['pass'])
                stack = []
                stack.append(self.endpoint)
                stack.append(self.postdata)
                stack.append(self.rest)
                stack.append(self.opts)
                self.send(endpoint='Myth/version')
                self.opts = stack.pop()
                self.rest = stack.pop()
                self.postdata = stack.pop()
                self.endpoint = stack.pop()
        except KeyError:
            # Proceed without authentication.
            pass

    def _validate_header(self, header):
        """
        Process the contents of the HTTP Server: header. Try to see
        what version the server is running on. The tested versions
        are kept in MYTHTV_VERSION_LIST and checked against responses
        like:

            MythTV/29-pre-5-g6865940-dirty Linux/3.13.0-85-generic UPnP/1.0.
            MythTV/28.0-10-g57c1afb Linux/4.4.0-21-generic UPnP/1.0.
            Linux 3.13.0-65-generic, UPnP/1.0, MythTV 0.27.20150622-1
        """

        if header is None:
            return {'Abort': 'No HTTP "Server from host {}:" header returned.'
                             .format(self.host)}

        for version in MYTHTV_VERSION_LIST:
            if re.search(version, header):
                self.server_version = version
                return

        return {'Abort': 'Tested on {}, not: {}.'.format(MYTHTV_VERSION_LIST,
                                                         header)}

    @property
    def get_server_version(self):
        """
        Returns the version of the back/frontend. Only works if send() has
        been called.
        """
        return self.server_version

    @property
    def get_opts(self):
        """
        Returns the all opts{}, whether set manually or automatically
        been called.
        """
        return self.opts

    @property
    def get_headers(self):
        """
        Returns the current headers.
        """
        return self.session.headers

# vim: set expandtab tabstop=4 shiftwidth=4 smartindent noai colorcolumn=80:
