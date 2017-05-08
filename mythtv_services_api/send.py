# -*- coding: utf-8 -*-

"""Basic access utilities."""

from __future__ import print_function
from __future__ import absolute_import

import re
import sys
import tempfile

try:
    import requests
    from requests.auth import HTTPDigestAuth
except ImportError:
    sys.exit('Install python-requests or python3-requests')

__version__ = '0.0.4'

SERVER_VERSION = 'Set to MythTV version after calls to send()'
SESSION = None

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
    a return (with the explaination) should be made.
    """

    return isinstance(response, dict)


def _set_missing_opts(opts):
    """Don't force the caller to set all of the options."""

    missing_opts = []

    if not isinstance(opts, dict):
        opts = {}

    for option in ('debug', 'noetag', 'nogzip', 'usexml', 'wrmi', 'wsdl'):
        try:
            opts[option]
        except (KeyError, TypeError):
            missing_opts.append(option)
            opts[option] = False

    if opts['debug'] and missing_opts:
        print('Debug: Missing opts set to False: {}'.format(missing_opts))

    return opts


def _form_url(host, port, endpoint, postdata, rest):
    """Basic sanity checks before making the URL."""

    if host == '':
        return {'Abort': 'No host name.'}

    if endpoint == '':
        return {'Abort': 'No endpoint (e.g. Myth/GetHostName.)'}

    if postdata and rest:
        return {'Abort': 'Use either postdata or rest.'}

    if rest == '' or rest is None:
        rest = ''
    else:
        rest = '?' + rest

    return 'http://{}:{}/{}{}'.format(host, port, endpoint, rest)


def _create_session(host, port, opts):
    "If one doesn't already exist, then create a new session."""

    global SESSION

    SESSION = requests.Session()
    SESSION.headers.update({'User-Agent': 'Python Services API Client v{}'
                                          .format(__version__)})
    if opts['noetag']:
        SESSION.headers.update({'Cache-Control': 'no-store'})
        SESSION.headers.update({'If-None-Match': ''})

    if opts['nogzip']:
        SESSION.headers.update({'Accept-Encoding': ''})
    else:
        SESSION.headers.update({'Accept-Encoding': 'gzip,deflate'})

    if opts['usexml']:
        SESSION.headers.update({'Accept': ''})
    else:
        SESSION.headers.update({'Accept': 'application/json'})

    if opts['debug']:
        print('Debug: New session')

    # TODO: Problem with the BE not accepting postdata in the initial
    # authorized query, Using a GET first as a workaround.

    try:
        if opts['user'] and opts['pass']:
            SESSION.auth = HTTPDigestAuth(opts['user'], opts['pass'])
            send(host=host, port=port, endpoint='Myth/version', opts=opts)
    except KeyError:
        # Proceed without authentication.
        pass


def _validate_opts(opts, postdata, rest, url):
    """Return an Abort if the options don't make sense"""

    if opts['debug']:
        print('Debug: URL = {}'.format(url))
        if postdata:
            print('Debug: The following postdata was included:')
            for key in postdata:
                print('  {:30} {}'.format(key, postdata[key]))

    if postdata and not opts['wrmi']:
        return {'Warning': 'wrmi=False'}

    if postdata and not isinstance(postdata, dict):
        return {'Abort': 'usage: postdata must be passed as a dict'}

    if opts['wsdl'] and (rest or postdata):
        return {'Abort': 'usage: rest/postdata aren\'t allowed with WSDL'}


def validate_server_header(header):
    """
    Process the contents of the HTTP Server: header. Try to see
    what version the server is running on. The tested versions
    are kept in MYTHTV_VERSION_LIST  and checked agaings responses
    like:

        MythTV/29-pre-5-g6865940-dirty Linux/3.13.0-85-generic UPnP/1.0.
        MythTV/0.28-pre-3094-g349d3a4 Linux/3.13.0-66-generic UPnP/1.0
        MythTV/28.0-10-g57c1afb Linux/4.4.0-21-generic UPnP/1.0.
        Linux 3.13.0-65-generic, UPnP/1.0, MythTV 0.27.20150622-1
    """

    global SERVER_VERSION

    if header is None:
        return {'Abort': 'No HTTP "Server:" header returned.'}

    for version in MYTHTV_VERSION_LIST:
        if re.search(version, header):
            SERVER_VERSION = version
            return

    return {'Abort': 'Tested on {}, not: {}.'.format(MYTHTV_VERSION_LIST,
                                                     header)}


def send(host='', port=6544, endpoint='', postdata=None, rest='', opts=None):
    """

    Form a URL and send it to the back/frontend. Error handling is done
    here too.

    Examples:
    =========

    from mythtv_services_api import send as api

    api.send(host='someHostName', endpoint='Myth/GetHostName')
    Returns:
    {'String': 'someBackend'}

    api.send(host='someFrontend', port=6547, endpoint='Frontend/GetStatus')
    Returns:
    {'FrontendStatus': {'AudioTracks':...

    Input:
    ======

    host:     Must be set and is the hostname or IP of the back/frontend.

    port:     Only needed if the backend is using a different port (unlikely)
              or set to 6547 for frontend endpoints. Defaults to 6544.

    endpoint: Must be set. Example: Myth/GetHostName

    postdata: May be set if the endpoint allows it. Used when information is
              to be added/changed/deleted. postdata is passed as a Python dict
              e.g. {'ChanId':1071, ...}. Don't use if rest is used. The HTTP
              method will be a POST (as opposed to a GET.)

              If using postdata, TAKE EXTREME CAUTION!!! Use opts['wrmi']=False
              1st, set opts['debug']=True and watch what's sent. When happy
              with the data, make wrmi True.

              N.B. The MythTV Services API is still evolving and the wise user
              will backup their DB before including postdata.

    rest:     May be set if the endpoint allows it. For example, endpoint=
              Myth/GetRecordedList, rest='Count=10&StorageGroup=Sports'
              Don't use if postdata is used. The HTTP method will be a GET.

    opts      SHORT DESCRIPTION:

              It's OK to call this function without any options set and:

                  • No "Debug:..." messages will print from this function
                  • If there's postdata, nothing will be sent to the server
                  • It will fail if the backend requires authorization (
                    user/pass would be required)

    DETAILS:

    opts is a dictionary of options that may be set in the calling program.
    Default values will be used if callers don't pass all or some of their
    own. The defaults are all False except for the user and pass.

    opts['debug']:   Set to True and some informational messages will be
                     printed.

    opts['noetag']:  Don't request the back/frontend to check for a matching
                     ETag. Mostly for testing.

    opts['nogzip']:  Don't request the back/frontend to gzip it's response.
                     Useful if watching protocol with a tool that doesn't
                     uncompress it.

    opts['user']:    Digest authentication.
    opts['pass']:

    opts['usexml']:  For testing only! If True, causes the backend to send its
                     response in XML rather than JSON. This will force an error
                     when parsing the response. Defaults to False.

    opts['wrmi']:    If True and there is postdata, the URL is actually sent
                     to the server.

                     If opts['wrmi'] is False and there is postdata, *NOTHING*
                     is sent to the server.

                     This is a failsafe that allows testing. Users can examine
                     what's about to be sent before doing it (wrmi = We Really
                     Mean It.)

    opts['wsdl']:    If True return WSDL from the back/frontend. Accepts no
                     rest or postdata. Just set endpoint, e.g. Content/wsdl

    Output:
    ======

    Either the response from the server in a Python dict format or an error
    message in a dict (currently with an 'Abort' or 'Warning' key.)

    Callers can handle the response like this:

        response = api.send(...)

        if list(response.keys())[0] in ['Abort', 'Warning']:
            {print|sys.exit}('{}'.format(list(response.values())[0]))

        normal processing...

    However, some errors returned by the server are in XML, e.g. if an
    endpoint is invalid. That will cause the JSON decoder to fail. Use
    the debug opt to view the failing response.

    Whenever send() is used, the global 'SERVER_VERSION' is set to the value
    returned by the back/frontend in the HTTP Server: header. It is saved as
    just the version, e.g. 0.28. Callers can check it and *may* choose to
    adjust their code work with other versions.

    """

    opts = _set_missing_opts(opts)

    url = _form_url(host, port, endpoint, postdata, rest)
    if _the_response_is_unexpected(url):
        return url

    if not SESSION:
        _create_session(host, port, opts)

    opts_response = _validate_opts(opts, postdata, rest, url)
    if _the_response_is_unexpected(opts_response):
        return opts_response

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
        if postdata:
            response = SESSION.post(url, data=postdata)
        else:
            response = SESSION.get(url)
    except exceptions:
        return {'Abort': 'Connection problem or Keyboard Interrupt, URL={}'
                         .format(url)}

    if response.status_code == 401:
        return {'Abort': 'Unauthorized (401) error. Need valid user/password.'}

    # TODO: Should handle redirects here:
    if response.status_code > 299:
        return {'Abort': 'Unexpected status returned: {}: URL was: {}'.format(
            response.status_code, url)}

    server_header = validate_server_header(response.headers['Server'])

    if _the_response_is_unexpected(server_header):
        return server_header

    ##############################################################
    # Finally, return the response after converting the JSON to  #
    # a dict. Or, or WSDL/XML/Image                              #
    ##############################################################

    if opts['wsdl']:
        return {'WSDL': response.text}

    try:
        opts['debug']
        print('Debug: 1st 60 bytes of response: {}'.format(response.text[:60]))
    except UnicodeEncodeError:
        pass

    if opts['usexml']:
        return response

    header, image_type = response.headers['Content-Type'].split('/')

    if header == 'image':
        handle, filename = tempfile.mkstemp(suffix='.' + image_type,)
        if opts['debug']:
            print('Debug: created {}, remember to delete it.'.format(filename))
        with open(filename, 'wb') as fd:
            for chunk in response.iter_content(chunk_size=8192):
                fd.write(chunk)
        return {'Image': filename}

    try:
        return response.json()
    except ValueError as err:
        return {'Abort': 'Set debug to see JSON parsing error: {}'.format(err)}
