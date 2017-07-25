#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This may not qualify for true unit tests, but some of the following are.

NOTE: The value of the TEST_* globals below must be changed manually for
the system under test!

ALSO: The user/pass opts are hardcoded to the default of admin/mythtv.
It's unlikely that most will even be running with digest protection on.
'''

import argparse
import logging
import unittest
from mythtv_services_api import (send as api, utilities as util)
from mythtv_services_api._version import __version__

global BACKEND
BACKEND = None

TEST_DVR_VERSION = '6.4'
TEST_DVR_ENDPOINT = 'Dvr/version'
TEST_HOST = 'mc0'
TEST_PORT = 6544
TEST_SERVER_VERSION = '29'
TEST_UTC_OFFSET = -18000

REC_STATUS_DATA = {
    # rec_status, expect
    -17: 'Unknown',
    -11: 'Missed',
    -10: 'Tuning',
    -9: 'Recorder Failed',
    -8: 'Tuner Busy',
    -7: 'Low Disk Space',
    -6: 'Manual Cancel',
    -5: 'Missed',
    -4: 'Aborted',
    -3: 'Recorded',
    -2: 'Recording',
    3: 'Currently Recorded',
    4: 'Earlier Showing',
    5: 'Max Recordings',
    6: 'Not Listed',
    12: 'Recorder Off-Line',
    13: 'Unknown',
}

def process_command_line():
    '''
    THIS DOESN'T SEEM TO WORK, THE unittest MODULE SEEMS TO OVERRIDE IT.
    LEAVING IT HERE FOR NOW.
    '''

    parser = argparse.ArgumentParser(description='Print Upcoming Programs',
                                     epilog='Default values are in ()s')

    mandatory = parser.add_argument_group('requrired arguments')

    parser.add_argument('--debug', action='store_true',
                        help='turn on debug messages (%(default)s)')

    parser.add_argument('--digest', type=str, metavar='<user:pass>',
                        help='digest username:password')

    mandatory.add_argument('--host', type=str, required=True,
                           metavar='<hostname>', help='backend hostname')

    parser.add_argument('--port', type=int, default=6544, metavar='<port>',
                        help='port number of the Services API (%(default)s)')

    parser.add_argument('--version', action='version', version='%(prog)s 0.11')

    return parser.parse_args()


# pylint: disable=protected-access
class MythTVServicesAPI(unittest.TestCase):
    ''' Test the MythTV Services API'''

    def setUp(self):
        '''
        Called before every one of the following test_*()s. Guarantee
        that the session's options are set to their default values
        and that UTC time is set.

        '''

        global BACKEND

        # self.longMessage = True

        if BACKEND:
            BACKEND.close_session()

        opts = {'user': 'admin', 'pass': 'mythtv'}
        BACKEND = api.Send(host=TEST_HOST)
        BACKEND.send(endpoint=TEST_DVR_ENDPOINT, opts=opts)
        util.get_utc_offset(backend=BACKEND)

    def test_access(self):
        '''
        Test basic backend access
        '''

        self.assertIsInstance(BACKEND, api.Send)
        self.assertEqual(BACKEND.send(endpoint=TEST_DVR_ENDPOINT)['String'],
                         TEST_DVR_VERSION)
        self.assertTrue(BACKEND.server_version == TEST_SERVER_VERSION)

    def test_default_opts(self):
        '''
        Test default option values

        All default values are False except timeout, which is 10.
        '''

        global BACKEND

        for key, value in BACKEND.get_opts.items():
            if key is 'timeout':
                self.assertEqual(value, 10)
            elif key is 'user' or key is 'pass':
                pass
            else:
                self.assertFalse(value)

        response = '{"String": "' + TEST_DVR_VERSION + '"}'
        self.assertEqual(BACKEND.send(endpoint=TEST_DVR_ENDPOINT,
                                      opts={'wsdl': True}), {'WSDL': response})

        session_options = {
            # option, expect
            'noetag': '{\'String\': ',
            'nogzip': '{\'String\': ',
            'usexml': '<?xml version="1.0" encoding="UTF-8"?><String>',
        }

        expected_headers = {
            # option, header, value (0, 1)
            'noetag': ('If-None-Match', ''),
            'nogzip': ('Accept-Encoding', ''),
            'usexml': ('Accept', ''),
        }

        for option, expect in session_options.items():
            BACKEND.close_session()
            BACKEND = api.Send(host=TEST_HOST)
            opts = {option: True, 'user': 'admin', 'pass': 'mythtv'}
            response = str(BACKEND.send(endpoint=TEST_DVR_ENDPOINT,
                                        opts=opts))

            self.assertIn(expect, response)

            self.assertEqual(BACKEND.get_headers(
                header=expected_headers[option][0]),
                             expected_headers[option][1])

    def test_digest(self):
        '''
        Verify that bad digest user and passwords fail. This test will
        turn on authentication, try a bad password (expecting to fail
        and then turn authentication off.
        '''

        global BACKEND

        put = 'Myth/PutSetting'

        kwargs = {'opts': {'user': 'admin', 'pass': 'mythtv', 'wrmi': True},
                  'postdata': {'Key': 'HTTP/Protected/Urls', 'Value': '/Myth'}
                 }
        self.assertEqual(BACKEND.send(endpoint=put, **kwargs),
                         {'bool': 'true'})

        BACKEND.close_session()
        BACKEND = api.Send(host=TEST_HOST)
        kwargs = {'opts': {'user': 'admin', 'pass': 'Xmythtv', 'wrmi': True},
                  'postdata': {'Key': 'HTTP/Protected/Urls', 'Value': '/Fail'}}
        self.assertRaises(RuntimeError, BACKEND.send, endpoint=put, **kwargs)

        BACKEND.close_session()
        BACKEND = api.Send(host=TEST_HOST)
        kwargs = {'opts': {'user': 'admin', 'pass': 'mythtv', 'wrmi': True},
                  'postdata': {'Key': 'HTTP/Protected/Urls', 'Value': '/Off'}}
        self.assertEqual(BACKEND.send(endpoint=put, **kwargs),
                         {'bool': 'true'})

    def test_headers_using_default_opts(self):
        '''
        Test headers with all options False
        '''

        user_agent = 'Python Services API v' + __version__
        headers_with_no_options_set = {
            # header, value
            'Accept-Encoding': 'gzip,deflate',
            'Connection': 'keep-alive',
            'User-Agent': user_agent,
            'Accept': 'application/json'
        }

        for header, value in headers_with_no_options_set.items():
            self.assertEqual(BACKEND.get_headers(header=header), value)

    def test_runtime_exceptions(self):
        '''
        Testing Runtime* exceptions

        In these tests, we're indirectly testing the _form_url() function.
        '''

        # empty endpoint combinations
        self.assertRaises(RuntimeError, BACKEND.send)
        self.assertRaises(RuntimeError, BACKEND.send, endpoint='')
        self.assertRaises(RuntimeError, BACKEND.send, endpoint=None)

        # invalid endpoint, backend will return a 404
        self.assertRaises(RuntimeError, BACKEND.send,
                          endpoint='Myth/InvalidEndpoint')

        # illegal rest and postdata
        args = {'endpoint': TEST_DVR_ENDPOINT}
        kwargs = {'rest': 'Who=Cares',
                  'opts': {'wrmi': True},
                  'postdata': {'Some': 'Junk'}}
        self.assertRaises(RuntimeError, BACKEND.send, *args, **kwargs)

        # Now check  _validate_postdata()

        args = {'endpoint': 'Myth/PutSetting'}
        kwargs = {'postdata': {'Key': 'FakeSetting', 'HostName': TEST_HOST}}

        # postdata not a dict, *kwargs is intentionally missing a *
        self.assertRaises(RuntimeError, BACKEND.send, *args, *kwargs)

        # wrmi=False
        self.assertRaises(RuntimeWarning, BACKEND.send, *args, **kwargs)

        # Finally, make sure wsdl can't be used with rest or postdata
        kwargs = {'opts': {'wrmi': True, 'wsdl': True},
                  'rest': 'Who=Cares'}
        self.assertRaises(RuntimeError, BACKEND.send, *args, **kwargs)

        kwargs = {'opts': {'wrmi': True, 'wsdl': True},
                  'postdata': {'Some': 'More Junk'}}
        self.assertRaises(RuntimeError, BACKEND.send, *args, **kwargs)

    def test_form_url(self):
        '''
        Test _form_url(), which has no exceptions. It just returns a URL,
        which is developed in the setUp() method. Watch out if the URL
        is changed there!
        '''

        url = 'http://{}:{}/{}'.format(TEST_HOST, TEST_PORT, TEST_DVR_ENDPOINT)
        self.assertEqual(BACKEND._form_url(), url)

    def test_validate_header(self):
        '''
        Test _validate_header() RuntimeError exceptions
        '''

        header = 'MythTV/99-pre-5-g6865940-dirty Linux/3.13.0-85-generic'

        self.assertRaises(RuntimeError, BACKEND._validate_header, None)
        self.assertRaises(RuntimeError, BACKEND._validate_header, '')
        self.assertRaises(RuntimeError, BACKEND._validate_header, header)

    def test_create_find_time(self):
        '''
        Test create_find_time()

        Name this function alphabetically after get_utc_offset() or else
        the offset won't be set.
        '''

        create_find_time_data = {
            # time: response
            None: None,
            '': None,
            '20170101 08:01:02': -1,
            '2017-01-01 09:01:02': -1,
            '2017-01-01T00:01:02': '19:01:02',
            '2017-01-01T00:01:03Z': '19:01:03',
            '2017-11-21T00:01:04Z': '19:01:04',
        }

        for time, response in create_find_time_data.items():
            self.assertEqual(util.create_find_time(time), response)

    def test_url_encode(self):
        '''
        Test url_encode()
        '''

        encode_test_data = {
            #source: response
            None: None,
            '': '',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'abcdefghijklmnopqrstuvwxyz': 'abcdefghijklmnopqrstuvwxyz',
            'Edición': 'Edici%C3%B3n',
            'A != B': 'A%20%21%3D%20B',
            '@#$%^&*()-={}[]': '%40%23%24%25%5E%26%2A%28%29-%3D%7B%7D%5B%5D',
            '~`|\\:;"\'<>?,./': '%7E%60%7C%5C%3A%3B%22%27%3C%3E%3F%2C./',
        }

        for source, response in encode_test_data.items():
            self.assertEqual(util.url_encode(value=source), response)

    def test_utc_to_local(self):
        '''
        Test utc_to_local()

        Test two "no keyword" cases 1st, then loop through various
        combinations of timestamps. Finally, test the omityear keyword.
        '''

        self.assertIsNone(util.utc_to_local(None), msg='Null utctime')
        self.assertIsNone(util.utc_to_local(''), msg='Empty utctime')

        utc_to_local_data = {
            # time, response
            None: None,
            '': None,
            '20170101 00:01:02': None,
            '2017-01-01 00:01:09': '2016-12-31 19:01:09',
            '2017-01-01 00:01:22': '2016-12-31 19:01:22',
        }

        for time, response in utc_to_local_data.items():
            self.assertEqual(util.utc_to_local(utctime=time), response)

        self.assertEqual(util.utc_to_local(utctime='2017-01-01T00:01:02Z',
                                           omityear=True), '12-31 19:01:02')

    def test_rec_status_to_string(self):
        '''
        Test rec_status_to_string()
        '''

        self.assertEqual(util.rec_status_to_string(None), None)
        self.assertEqual(util.rec_status_to_string(backend=None), None)

        self.assertIsInstance(REC_STATUS_DATA, dict, msg='None case')
        for rec_status, expect in REC_STATUS_DATA.items():
            self.assertEqual(util.rec_status_to_string(backend=BACKEND,
                                                       rec_status=rec_status),
                             expect)

    def test_rec_status_to_string_cache(self):
        '''
        Test rec_status_to_string() for cached strings

        Same as previous test, but the strings should be in cache now. The
        only way to check is to look at the backend log (with -v http turned
        on.) Watch for: Connection -1 closed. 17 requests were handled from
        the above.
        '''

        self.assertIsInstance(REC_STATUS_DATA, dict, msg='None case')
        for rec_status, expect in REC_STATUS_DATA.items():
            self.assertEqual(util.rec_status_to_string(backend=BACKEND,
                                                       rec_status=rec_status),
                             expect)

    def test_rec_type_to_string(self):
        '''
        Test rec_type_to_string()
        '''

        self.assertEqual(util.rec_type_to_string(backend=None,
                                                 rec_type=1), None)

        rec_type_data = {
            # rec_type: expect
            # TODO: None case seems odd, expected the same as 0
            None: 'Override Recording',
            0: 'Not Recording',
            1: 'Single Record',
            3: 'Not Recording',
            4: 'Record All',
            5: 'Record Weekly',
        }

        for rec_type, expect in rec_type_data.items():
            self.assertEqual(util.rec_type_to_string(backend=BACKEND,
                                                     rec_type=rec_type),
                             expect)

    def test_dup_method_to_string(self):
        '''
        Test dup_method_to_string()
        '''

        # TODO: mythbackend isn't handling this endpoint correctly.
        dup_method_and_response = {
            # method: response
            -5: 'Subtitle and Description',
            -4: 'Subtitle and Description',
            -3: 'Subtitle and Description',
            -2: 'Subtitle and Description',
            -1: 'Subtitle and Description',
            0: 'Subtitle and Description',
            1: 'Subtitle and Description',
            2: 'Subtitle and Description',
            3: 'Subtitle and Description',
            4: 'Subtitle and Description',
            5: 'Subtitle and Description',
        }

        for method, response in dup_method_and_response.items():
            self.assertEqual(util.dup_method_to_string(
                backend=BACKEND, dup_method=method), response)

if __name__ == '__main__':

    # Can't make this work with unittests: ARGS = process_command_line()
    ARGS = {'debug': False}
    logging.basicConfig(level=logging.DEBUG
                        if ARGS['debug'] else logging.CRITICAL)
    logging.getLogger('requests.packages.urllib3').setLevel(logging.ERROR)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

    unittest.main()

# :!./% --verbose
# :!./% --verbose MythTVServicesAPI
# :!./% --verbose MythTVServicesAPI.test_default_opts
# :!./% --verbose MythTVServicesAPI.test_utilities
# :!./% --verbose MythTVServicesAPI.test_rec_status_to_string
# :!./% --verbose MythTVServicesAPI.test_runtime_exceptions
# :!./% --verbose MythTVServicesAPI.test_utc_to_local
# :!./% --verbose MythTVServicesAPI.test_digest

# vim: set expandtab tabstop=4 shiftwidth=4 smartindent colorcolumn=80:
