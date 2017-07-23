#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This may not qualify for true unit tests, but some of the following are.

NOTE: The value of TEST_HOST and TEST_UTC_OFFSET (below) must be changed
to the backend under test and current time zone offset respectively.
'''

import argparse
import unittest
from mythtv_services_api import (send as api, utilities as util)

global BACKEND
BACKEND = None

TEST_HOST = 'mc0'
TEST_UTC_OFFSET = -18000
TEST_SERVER_VERSION = '29'

REC_STATUS_DATA = [
    ['Unknown', -17],
    ['Missed', -11],
    ['Tuning', -10],
    ['Recorder Failed', -9],
    ['Tuner Busy', -8],
    ['Low Disk Space', -7],
    ['Manual Cancel', -6],
    ['Missed', -5],
    ['Aborted', -4],
    ['Recorded', -3],
    ['Recording', -2],
    ['Currently Recorded', 3],
    ['Earlier Showing', 4],
    ['Max Recordings', 5],
    ['Not Listed', 6],
    ['Recorder Off-Line', 12],
    ['Unknown', 13],
]

def process_command_line():
    '''
    THIS DOESN'T SEEM TO WORK, THE unittest MODULE SEEMS TO OVERRIDES IT OR
    MAYBE HAS IT'S OWN ARGPARSE?
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

    parser.add_argument('--version', action='version', version='%(prog)s 0.10')

    return parser.parse_args()


class MythTVServicesAPI(unittest.TestCase):
    ''' Test the MythTV Services API'''

    def setUp(self):
        '''
        Called before every one of the following test()s. Guarantee
        that the session's options are set to their default values
        and that UTC time is set.
        '''

        global BACKEND

        if BACKEND:
            BACKEND.close_session()

        BACKEND = api.Send(host=TEST_HOST)
        BACKEND.send(endpoint='Dvr/version')

    def test_access(self):
        '''
        Test basic backend access

        Also, do the get_utc_offset() tests here so that the UTC_OFFSET
        will be set for future tests.

        Alphabetically, this function must be 1st (e.g. name any other
        function that needs test_a...() test_ad...()).
        '''

        self.assertEqual(BACKEND.send(endpoint='Dvr/version')['String'], '6.4')

        self.assertTrue(BACKEND.server_version == TEST_SERVER_VERSION)
        self.assertFalse(BACKEND.server_version == '0.26')

        self.assertEqual(util.get_utc_offset(backend=BACKEND), TEST_UTC_OFFSET)
        self.assertEqual(util.get_utc_offset(backend=None), -1)

    def test_default_opts(self):
        '''
        Test default option values

        All default values are False except timeout, which is 10.
        '''

        global BACKEND

        for key, value in BACKEND.get_opts.items():
            if key is 'timeout':
                self.assertEqual(value, 10)
            else:
                self.assertFalse(value)

        self.assertEqual(BACKEND.send(endpoint='Myth/version',
                                      opts={'wsdl': True}),
                         {'WSDL': '{"String": "5.0"}'})

        session_options = {
            'noetag': '{\'String\': ',
            'nogzip': '{\'String\': ',
            'usexml': '<?xml version="1.0" encoding="UTF-8"?><String>',
        }

        expected_headers = {
            'noetag': ('If-None-Match', ''),
            'nogzip': ('Accept-Encoding', ''),
            'usexml': ('Accept', ''),
        }

        for option, expect in session_options.items():
            BACKEND.close_session()
            BACKEND = api.Send(host=TEST_HOST)
            response = str(BACKEND.send(endpoint='Myth/version',
                                        opts={option: True}))
            self.assertIn(expect, response)

            self.assertEqual(BACKEND.get_headers(
                header=expected_headers[option][0]),
                             expected_headers[option][1])

    def test_headers_with_default_opts(self):
        '''
        Test headers with all options False
        '''

        headers_with_no_options_set = {
            'Accept-Encoding': 'gzip,deflate',
            'Connection': 'keep-alive',
            'User-Agent': 'Python Services API v0.1.5',
            'Accept': 'application/json'
        }

        for header, value in headers_with_no_options_set.items():
            self.assertEqual(BACKEND.get_headers(header=header), value)

    def test_runtime_exceptions(self):
        '''
        Testing Runtime* exceptions

        In these tests, we're indirectly testing the _form_url() function.
        '''

        # invalid endpoint combinations
        self.assertRaises(RuntimeError, BACKEND.send)
        self.assertRaises(RuntimeError, BACKEND.send, endpoint='')
        self.assertRaises(RuntimeError, BACKEND.send, endpoint=None)

        # bad endpoint, backend will return a 404
        self.assertRaises(RuntimeError, BACKEND.send, 'Myth/InvalidEndpoint')

        # rest and postdata
        args = {'endpoint': 'Myth/version'}
        kwargs = {'rest': 'Who=Cares',
                  'opts': {'wrmi': True},
                  'postdata': {'Some': 'Junk'}}
        self.assertRaises(RuntimeError, BACKEND.send, *args, **kwargs)

        args = {'endpoint': 'Myth/PutSetting'}

        # Now do _validate_postdata()

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
        Test _form_url(), which has no exceptions, just return a URL,
        which is developed in the setUp() method.
        '''

        url = 'http://{}:6544/Dvr/version'.format(TEST_HOST)
        # pylint: disable=protected-access
        self.assertEqual(BACKEND._form_url(), url)
        # pylint: enable=protected-access

    def test_validate_header(self):
        '''
        Test _validate_header() RuntimeError exceptions
        '''

        # pylint: disable=protected-access
        self.assertRaises(RuntimeError, BACKEND._validate_header, None)
        self.assertRaises(RuntimeError, BACKEND._validate_header, '')
        header = 'MythTV/99-pre-5-g6865940-dirty Linux/3.13.0-85-generic'
        self.assertRaises(RuntimeError, BACKEND._validate_header, header)
        # pylint: enable=protected-access

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
            '20170101 00:01:02': -1,
            '2017-01-01 00:01:02': -1,
            '2017-01-01T00:01:02': '19:01:02',
            '2017-01-01T00:01:02Z': '19:01:02',
            '2017-11-21T00:01:02Z': '19:01:02',
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
        }

        for source, response in encode_test_data.items():
            self.assertEqual(util.url_encode(value=source), response)

    def test_utc_to_local(self):
        '''
        Test utc_to_local()

        Test two "no keyword" cases 1st, then loop through various
        timestamps. Finally, test the omityear keyword.
        '''

        self.assertEqual(util.get_utc_offset(backend=BACKEND), TEST_UTC_OFFSET)
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

        for expect, rec_status in REC_STATUS_DATA:
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

        for expect, rec_status in REC_STATUS_DATA:
            self.assertEqual(util.rec_status_to_string(backend=BACKEND,
                                                       rec_status=rec_status),
                             expect)

    def test_rec_type_to_string(self):
        '''
        Test rec_type_to_string()
        '''

        self.assertEqual(util.rec_type_to_string(backend=None,
                                                 rec_type=1), None)

        # TODO: looks like a bug, rec_type 0 = Override Recording
        #self.assertEqual(util.rec_type_to_string(backend=BACKEND,
        #                                         rec_type=None), None)

        rec_type_data = {
            # rec_type: expected
            1: 'Single Record',
            3: 'Not Recording',
            4: 'Record All',
            5: 'Record Weekly',
        }

        for rec_type, expected in rec_type_data.items():
            self.assertEqual(util.rec_type_to_string(backend=BACKEND,
                                                     rec_type=rec_type),
                             expected)

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

    unittest.main()

# :!./% --verbose
# :!./% --verbose MythTVServicesAPI
# :!./% --verbose MythTVServicesAPI.test_default_opts
# :!./% --verbose MythTVServicesAPI.test_utilities
# :!./% --verbose MythTVServicesAPI.test_rec_status_to_string
# :!./% --verbose MythTVServicesAPI.test_runtime_exceptions

# vim: set expandtab tabstop=4 shiftwidth=4 smartindent colorcolumn=80:
