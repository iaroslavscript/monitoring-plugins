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
import sys
import traceback

try:
    import requests
except ImportError:
    from python_extras import requests


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
    parser.add_argument('--host', help='Kibana host (default: localhost)', default='localhost')
    parser.add_argument('--port', help='Kibana port (default: 5601)', default='5601')
    parser.add_argument('--no-server', help='No checking kibana health status', action='store_true')
    parser.add_argument('--no-modules', help='No checking kibana modules health status', action='store_true')
  
    return parser


def parse_args(parser):

    config = parser.parse_args()

    if config.host.endswith('/'):
        config.host = config.host[:-1]

    if config.no_server and config.no_modules:
        parser.error('Implicit requirements: options --no-server and --no-modules can not be used together')

    return config


def kibana_request(config, url):
    
    try:
        r = requests.get('http://{}:{}/{}'.format(config.host, config.port, url))

        r.raise_for_status()
        result = r.json()

    except requests.exceptions.RequestException as e:

        response_msg = ''
        if e.response is not None:
            response_msg = 'status_code: {}, headers={}'.format(e.response.status_code, e.response.headers)
        
        raise SensuChecksException(ERRORCODE_UNKNOWN, 'UNKNOWN: HTTP error occured, msg={}, {}'.format(e, response_msg))

    except requests.exceptions.BaseHTTPError as e:
        
        raise SensuChecksException(ERRORCODE_UNKNOWN, 'UNKNOWN: HTTP error occured, {}'.format(e))
    
    return result


def check_kibana_health(metrics):

    health_state = metrics['status']['overall']['state']
    health_title = metrics['status']['overall']['title']
    health_nickname = metrics['status']['overall']['nickname']

    if 'red' == health_state:
        raise SensuChecksException(ERRORCODE_CRITICAL, 'CRITICAL: Kibana health status state={}, title={}, msg={}'.format(health_state, health_title, health_nickname))

    elif 'yellow' == health_state:
        raise SensuChecksException(ERRORCODE_WARNING, 'WARNING: Kibana health status state={}, title={}, msg={}'.format(health_state, health_title, health_nickname))

    elif 'green' != health_state:
        raise SensuChecksException(ERRORCODE_UNKNOWN, 'UNKNOWN: Kibana health status state={}, title={}, msg={}'.format(health_state, health_title, health_nickname))
    
    return 'Kibana health status state={}, title={}, msg={}'.format(health_state, health_title, health_nickname)


def check_modules_health(metrics):

    for item in metrics['status']['statuses']:
        health_state = item['state']
        msg = item['message']
        name = item['name']

        if 'red' == health_state:
            raise SensuChecksException(ERRORCODE_CRITICAL, 'CRITICAL: Kibana module "{}" health status state={}, msg={}'.format(name, health_state, msg))

        elif 'yellow' == health_state:
            raise SensuChecksException(ERRORCODE_WARNING, 'WARNING: Kibana module "{}" health status state={}, msg={}'.format(name, health_state, msg))

        elif 'green' != health_state:
            raise SensuChecksException(ERRORCODE_UNKNOWN, 'UNKNOWN: Kibana module "{}" health status state={}, msg={}'.format(name, health_state, msg))

    return 'Kibana modules health status state is green'


def check_kibana(config, metrics):

    status_server = ''
    status_modules = ''

    if not config.no_server:
        status_server = check_kibana_health(metrics)

    if not config.no_modules:
        status_modules = check_modules_health(metrics)

    raise SensuChecksException(ERRORCODE_OK, ';'.join(list(filter(bool, (status_server,status_modules)))))


def main():
    try:
        parser = create_parser()
        config = parse_args(parser)
        metrics = kibana_request(config, 'api/status')
        check_kibana(config, metrics)

    except SensuChecksException as e:
        print(e.msg)
        sys.exit(e.error_code)

    except Exception:
        print('UNKNOWN: unexpected exception occured')
        traceback.print_exc()
        sys.exit(ERRORCODE_UNKNOWN)


if __name__ == '__main__':
    main()

