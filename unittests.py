#!/usr/bin/env python3

''' This is a first crack at unit testing the Services API stuff '''

import argparse
import unittest
from mythtv_services_api import (send as api, utilities as util)

global BACKEND

HOST = 'mc0'

def process_command_line():
    '''
    THIS DOESN'T SEEM TO WORK, THE unittest MODULE TAKES PLACE OR
    HAS IT'S OWN ARGPARSE.
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
    ''' Test the Services API basics...'''

    def test_access(self):
        ''' Test basic backend access '''

        self.assertEqual(BACKEND.send(endpoint='Dvr/version')
                         ['String'], '6.4')
        self.assertTrue(BACKEND.server_version == '29')
        self.assertFalse(BACKEND.server_version == '0.28')

    def test_opts(self):
        ''' Test default options '''

        for key, value in BACKEND.get_opts.items():
            if key == 'timeout':
                self.assertEqual(value, 10)
                continue
            self.assertFalse(value)

    def test_runtime_warnings(self):
        ''' Testing Runtime* exceptions '''

        self.assertRaises(RuntimeError, BACKEND.send, endpoint='')
        self.assertRaises(RuntimeError, BACKEND.send, endpoint=None)
        args = {'endpoint': 'Myth/PutSetting'}
        kwargs = {'postdata': {'Key': 'BackendServerIP', 'HostName': HOST}}
        self.assertRaises(RuntimeWarning, BACKEND.send, args, kwargs)

    def test_get_utc_offset(self):
        ''' Test get_utc_offset() '''

        self.assertEqual(util.get_utc_offset(backend=BACKEND), -18000)
        self.assertEqual(util.get_utc_offset(backend=None), -1)

    def test_url_encode(self):
        ''' Test url_encode() '''

        self.assertEqual(util.url_encode(value=None), None)
        self.assertEqual(util.url_encode(value=''), '')
        self.assertEqual(util.url_encode(value='Edición'), 'Edici%C3%B3n')
        self.assertEqual(util.url_encode(value='Dog != Cat'),
                         'Dog%20%21%3D%20Cat')

    def test_h_create_find_time(self):
        ''' Test create_find_time() '''

        self.assertEqual(util.create_find_time(None), None)
        self.assertEqual(util.create_find_time(''), None)
        self.assertEqual(util.create_find_time('20170101 00:01:02'), -1)
        self.assertEqual(util.create_find_time('2017-01-01 00:01:02'), -1)
        self.assertEqual(util.create_find_time('2017-01-01T00:01:02'),
                         '19:01:02')
        self.assertEqual(util.create_find_time('2017-01-01T00:01:02Z'),
                         '19:01:02')

    def test_utc_to_local(self):
        ''' Test utc_to_local() '''

        self.assertEqual(util.utc_to_local(None), None)
        self.assertEqual(util.utc_to_local(utctime=None), None)
        self.assertEqual(util.utc_to_local(utctime=''), None)
        self.assertEqual(util.utc_to_local(utctime='20170101 00:01:02'), None)
        self.assertEqual(util.utc_to_local(utctime='2017-01-01 00:01:02'),
                         '2016-12-31 19:01:02')
        self.assertEqual(util.utc_to_local(utctime='2017-01-01T00:01:02',
                                           omityear=True), '12-31 19:01:02')
        self.assertEqual(util.utc_to_local(utctime='2017-01-01T00:01:02Z',
                                           omityear=True), '12-31 19:01:02')

    def test_rec_status_to_string(self):
        ''' Test rec_status_to_string() '''

        self.assertEqual(util.rec_status_to_string(None), None)
        self.assertEqual(util.rec_status_to_string(backend=None), None)
        self.assertEqual(util.rec_status_to_string(backend=BACKEND),
                         'Not Recording')
        self.assertEqual(util.rec_status_to_string(backend=BACKEND,
                                                   rec_status=-17), 'Unknown')
        self.assertEqual(util.rec_status_to_string(backend=BACKEND,
                                                   rec_status=-3), 'Recorded')
        self.assertEqual(util.rec_status_to_string(backend=BACKEND,
                                                   rec_status=13), 'Unknown')

        self.assertEqual(util.rec_type_to_string(backend=None,
                                                 rec_type=1), None)
        # TODO: looks like a bug, no rec_type = Override Recording
        #self.assertEqual(util.rec_type_to_string(backend=BACKEND,
        #                                         rec_type=None), None)
        self.assertEqual(util.rec_type_to_string(backend=BACKEND,
                                                 rec_type=1), 'Single Record')
        self.assertEqual(util.rec_type_to_string(backend=BACKEND,
                                                 rec_type=3), 'Not Recording')
        self.assertEqual(util.rec_type_to_string(backend=BACKEND,
                                                 rec_type=4), 'Record All')
        self.assertEqual(util.rec_type_to_string(backend=BACKEND,
                                                 rec_type=5), 'Record Weekly')

    def test_dup_method_to_string(self):
        ''' Test dup_method_to_string() '''

        # TODO: mythbackend isn't handling this endpoint...
        dup_method_tests = {
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

        for dup_method, dup_string in dup_method_tests.items():
            self.assertEqual(util.dup_method_to_string(
                backend=BACKEND, dup_method=dup_method), dup_string)

if __name__ == '__main__':

    global BACKEND
    BACKEND = api.Send(host=HOST)
    unittest.main()

# :!% --verbose MythTVServicesAPI.test_utilities

# vim: set expandtab tabstop=4 shiftwidth=4 smartindent colorcolumn=80:
