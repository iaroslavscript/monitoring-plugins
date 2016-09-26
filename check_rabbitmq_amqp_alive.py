#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# 
# Copyright (c) 2016 Iaroslav Akimov <iaroslavscript@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import argparse
import os
import subprocess
import socket
import sys
import time
import traceback

try:
    import pika
except ImportError:
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'python_extras'))
    )
    import pika


ERRORCODE_OK = 0 
ERRORCODE_WARNING = 1 
ERRORCODE_CRITICAL = 2
ERRORCODE_UNKNOWN = 3


class SensuChecksException(Exception):
    def __init__(self, error_code, msg):
        super(SensuChecksException, self).__init__((error_code, msg,))
        self.error_code = error_code
        self.msg = msg


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='default: localhost', default='localhost')
    parser.add_argument('--port', help='default: 5672', default=5672, type=int)
    parser.add_argument('--user', help='default: guest', default='guest')
    parser.add_argument('--password', help='default: guest', default='guest')
    parser.add_argument('--vhost', help='VHOST (use / instead of %2F)', default='/')
    
    return parser


def parse_args(parser):
    config = parser.parse_args()

    if config.host.endswith('/'):
        config.host = config.host[:-1]

    return config


def amqp_request(config):

    try:
        credentials = pika.PlainCredentials(config.user, config.password)
        parameters = pika.ConnectionParameters(
            host=config.host,
            port=config.port,
            virtual_host=config.vhost,
            credentials=credentials,
        )
        connection = pika.BlockingConnection( parameters )
        channel = connection.channel()
        
        if not all(( connection.is_open, channel.is_open)):
            raise SensuChecksException(ERRORCODE_UNKNOWN, 'UNKNOWN: Unable to open connection/channel (no error returned)')

    except pika.exceptions.AMQPConnectionError as e:
        raise SensuChecksException(ERRORCODE_CRITICAL, 'CRITICAL: AMQP connection error occured, {!r}, type:{}'.format(e, type(e)))
    
    raise SensuChecksException(ERRORCODE_OK, 'AMQP connection is OK')


def main():
    parser = create_parser()
    config = parse_args(parser)
    
    try:
        metrics_json = amqp_request(config)
        
    except SensuChecksException as e:
        print(e.msg)
        sys.exit(e.error_code)

    except Exception:
        print('UNKNOWN: unexpected exception occured')
        traceback.print_exc()        
        sys.exit(ERRORCODE_UNKNOWN)


if __name__ == '__main__':
    main()

