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
import re
import socket
import subprocess
import sys
import time
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
    parser.add_argument('--host', help='default: localhost', default='localhost')
    parser.add_argument('--port', help='default: 15672', default='15672')
    parser.add_argument('--user', help='default: guest', default='guest')
    parser.add_argument('--password', help='default: guest', default='guest')
    parser.add_argument('--scheme', help='Metric naming scheme, text to prepend to $queue_name.$metric')
    parser.add_argument('--vhost-pattern', help='Regular expression for filtering the RabbitMQ vhost')
    parser.add_argument('--queue-pattern', help='Regular expression for filtering queues')

    parser.add_argument('--messages-min-w', help='min warning for metric message count', type=float)
    parser.add_argument('--messages-min-c', help='min critical for metric message count', type=float)
    parser.add_argument('--messages-max-w', help='max warning for metric message count', type=float)
    parser.add_argument('--messages-max-c', help='max critical for metric message count', type=float)
    
    parser.add_argument('--consumers-min-w', help='min warning for metric consumer count', type=float)
    parser.add_argument('--consumers-min-c', help='min critical for metric consumer count', type=float)
    parser.add_argument('--consumers-max-w', help='max warning for metric consumer count', type=float)
    parser.add_argument('--consumers-max-c', help='max critical for metric consumer count', type=float)

    parser.add_argument('--avg-egress-rate-min-w', help='min warning for metric average egress rate', type=float)
    parser.add_argument('--avg-egress-rate-min-c', help='min critical for metric average egress rate', type=float)
    parser.add_argument('--avg-egress-rate-max-w', help='max warning for metric average egress rate', type=float)
    parser.add_argument('--avg-egress-rate-max-c', help='max critical for metric average egress rate', type=float)
    
    parser.add_argument('--drain-time-min-w', help='min warning for metric drain time, which is the time a queue will take to reach 0 based on the egress rate', type=float)
    parser.add_argument('--drain-time-min-c', help='min critical for metric drain time, which is the time a queue will take to reach 0 based on the egress rate', type=float)
    parser.add_argument('--drain-time-max-w', help='max warning for metric drain time, which is the time a queue will take to reach 0 based on the egress rate', type=float)
    parser.add_argument('--drain-time-max-c', help='max critical for metric drain time, which is the time a queue will take to reach 0 based on the egress rate', type=float)

    return parser


def rabbitmq_request(config, url): 

    if url.startswith('/'):
        url = url[1:]
    
    try:
        r = requests.get(
            'http://{}:{}/{}'.format(config.host, config.port, url),
            auth=(config.user, config.password),
        )

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


def parse_queue_metrics(metrics_json):

    metrics = []

    for queue in metrics_json:

        queue_messages = 0  if 'messages' not in queue  or  not queue['messages']  else queue['messages']
        drain_time = 0
        queue_metrics = {}

        try:
            drain_time = int(queue_messages / queue['backing_queue_status']['avg_egress_rate'])
        except ZeroDivisionError:
            pass

        queue_metrics['vhost'] = queue['vhost']
        queue_metrics['queue_name'] = queue['name']
        queue_metrics['drain_time'] = drain_time
        queue_metrics['messages'] = queue_messages
        queue_metrics['consumers'] = queue['consumers']
        queue_metrics['avg_egress_rate'] = queue['backing_queue_status']['avg_egress_rate']

        metrics.append(queue_metrics)

    return metrics


def print_metrics(config, metrics):

    timestamp = int(time.time())
    scheme = config.scheme  if config.scheme is not None  else '{}.rabbitmq'.format(socket.gethostname())

    for queue_metrics in metrics:
        for metrics_name,value in queue_metrics.items():
            if metrics_name not in ['vhost', 'queue_name']:
                print( '{}.{}.{} {} {}'.format( scheme, queue_metrics['queue_name'], metrics_name, value, timestamp))


def check_value(metric_field, metrics, min_w, min_c, max_w, max_c):
    
    is_not_none = lambda x: x is not None
    
    if any(filter(is_not_none, (min_w, min_c, max_w, max_c))):
        
        value_list = []            
        
        for queue_metrics in metrics:
            
            value = queue_metrics.get(metric_field)
            value_f = float(value)
            value_list.append(value_f)
            desc = '(vhost: {} queue: {})'.format(queue_metrics['vhost'], queue_metrics['queue_name'])

            if ( min_c is not None ) and ( value_f <= float(min_c) ):
                raise SensuChecksException(ERRORCODE_CRITICAL, "CRITICAL: metric {} = {} is lower or equal than {} {}".format(metric_field, value, min_c, desc))

            if ( max_c is not None ) and ( value_f >= float(max_c) ):
                raise SensuChecksException(ERRORCODE_CRITICAL, "CRITICAL: metric {} = {} is higher or equal than {} {}".format(metric_field, value, max_c, desc))

            if ( min_w is not None ) and ( value_f <= float(min_w) ):
                raise SensuChecksException(ERRORCODE_WARNING, "WARNING: metric {} = {} is lower or equal than {} {}".format(metric_field, value, min_w, desc))

            if ( max_w is not None ) and ( value_f >= float(max_w) ):
                raise SensuChecksException(ERRORCODE_WARNING, "WARNING: metric {} = {} is higher or equal than {} {}".format(metric_field, value, max_w, desc))

        average_value = float(sum(sorted(value_list)))/len(value_list)

        raise SensuChecksException(ERRORCODE_OK, "metric {} = {} (average value of all queues/vhosts)".format(metric_field, average_value))


def filter_metrics(config, metrics):

    vhost_filter_fn = lambda x: config.vhost_pattern.match(x['vhost'])
    queue_filter_fn = lambda x: config.queue_pattern.match(x['queue_name'])

    if config.vhost_pattern:
        
        metrics = list(filter(vhost_filter_fn, metrics))

    if config.queue_pattern:
        metrics = list(filter(queue_filter_fn, metrics))

    if not metrics:
        raise SensuChecksException(ERRORCODE_UNKNOWN, "UNKNOWN: no metrics to check")

    return metrics


def apply_checks(config, metrics):

    check_value(
        'messages',
        metrics,
        config.messages_min_w,
        config.messages_min_c,
        config.messages_max_w,
        config.messages_max_c,
    )

    check_value(
        'consumers',
        metrics,
        config.consumers_min_w,
        config.consumers_min_c,
        config.consumers_max_w,
        config.consumers_max_c,
    )

    check_value(
        'avg_egress_rate',
        metrics,
        config.avg_egress_rate_min_w,
        config.avg_egress_rate_min_c,
        config.avg_egress_rate_max_w,
        config.avg_egress_rate_max_c,
    )

    check_value(
        'drain_time',
        metrics,
        config.drain_time_min_w,
        config.drain_time_min_c,
        config.drain_time_max_w,
        config.drain_time_max_c,
    )

    print_metrics(config, metrics)


def parse_args(parser):
    config = parser.parse_args()

    if config.host.endswith('/'):
        config.host = config.host[:-1]

    argument_name = ''
    try:
        if config.vhost_pattern:
            argument_name = '--vhost-pattern'
            config.vhost_pattern = re.compile(config.vhost_pattern, re.IGNORECASE)

        if config.queue_pattern:
            argument_name = '--queue-pattern'
            config.queue_pattern = re.compile(config.queue_pattern, re.IGNORECASE)

    except re.error as e:
        parser.error('argument {} incorrent regular expression: {}'.format(argument_name, e))

    return config


def main():
    parser = create_parser()
    config = parse_args(parser)
    
    try:
        metrics_json = rabbitmq_request(config, 'api/queues')
        metrics = parse_queue_metrics(metrics_json)
        metrics = filter_metrics(config, metrics)    
        apply_checks(config, metrics)
    except SensuChecksException as e:
        print(e.msg)
        sys.exit(e.error_code)

    except Exception:
        print('UNKNOWN: unexpected exception occured')
        traceback.print_exc()        
        sys.exit(ERRORCODE_UNKNOWN)


if __name__ == '__main__':
    main()

