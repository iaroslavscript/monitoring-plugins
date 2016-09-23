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
import subprocess
import socket
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
    
    parser.add_argument('--queue-msg-count-min-w', help='min warning for metric queue_totals.messages.count', type=float)
    parser.add_argument('--queue-msg-count-min-c', help='min critical for metric queue_totals.messages.count', type=float)
    parser.add_argument('--queue-msg-count-max-w', help='max warning for metric queue_totals.messages.count', type=float)
    parser.add_argument('--queue-msg-count-max-c', help='max critical for metric queue_totals.messages.count', type=float)
    parser.add_argument('--queue-msg-rate-min-w', help='min warning for metric queue_totals.messages.rate', type=float)
    parser.add_argument('--queue-msg-rate-min-c', help='min critical for metric queue_totals.messages.rate', type=float)
    parser.add_argument('--queue-msg-rate-max-w', help='max warning for metric queue_totals.messages.rate', type=float)
    parser.add_argument('--queue-msg-rate-max-c', help='max critical for metric queue_totals.messages.rate', type=float)

    parser.add_argument('--queue-msg-unack-count-min-w', help='min warning for metric queue_totals.messages_unacknowledged.count', type=float)
    parser.add_argument('--queue-msg-unack-count-min-c', help='min critical for metric queue_totals.messages_unacknowledged.count', type=float)
    parser.add_argument('--queue-msg-unack-count-max-w', help='max warning for metric queue_totals.messages_unacknowledged.count', type=float)
    parser.add_argument('--queue-msg-unack-count-max-c', help='max critical for metric queue_totals.messages_unacknowledged.count', type=float)
    parser.add_argument('--queue-msg-unack-rate-min-w', help='min warning for metric queue_totals.messages_unacknowledged.rate', type=float)
    parser.add_argument('--queue-msg-unack-rate-min-c', help='min critical for metric queue_totals.messages_unacknowledged.rate', type=float)
    parser.add_argument('--queue-msg-unack-rate-max-w', help='max warning for metric queue_totals.messages_unacknowledged.rate', type=float)
    parser.add_argument('--queue-msg-unack-rate-max-c', help='max critical for metric queue_totals.messages_unacknowledged.rate', type=float)

    parser.add_argument('--queue-msg-ready-count-min-w', help='min warning for metric queue_totals.messages_ready.count', type=float)
    parser.add_argument('--queue-msg-ready-count-min-c', help='min critical for metric queue_totals.messages_ready.count', type=float)
    parser.add_argument('--queue-msg-ready-count-max-w', help='max warning for metric queue_totals.messages_ready.count', type=float)
    parser.add_argument('--queue-msg-ready-count-max-c', help='max critical for metric queue_totals.messages_ready.count', type=float)
    parser.add_argument('--queue-msg-ready-rate-min-w', help='min warning for metric queue_totals.messages_ready.rate', type=float)
    parser.add_argument('--queue-msg-ready-rate-min-c', help='min critical for metric queue_totals.messages_ready.rate', type=float)
    parser.add_argument('--queue-msg-ready-rate-max-w', help='max warning for metric queue_totals.messages_ready.rate', type=float)
    parser.add_argument('--queue-msg-ready-rate-max-c', help='max critical for metric queue_totals.messages_ready.rate', type=float)

    parser.add_argument('--msg-publish-count-min-w', help='min warning for metric message_stats.publish.count', type=float)
    parser.add_argument('--msg-publish-count-min-c', help='min critical for metric message_stats.publish.count', type=float)
    parser.add_argument('--msg-publish-count-max-w', help='max warning for metric message_stats.publish.count', type=float)
    parser.add_argument('--msg-publish-count-max-c', help='max critical for metric message_stats.publish.count', type=float)
    parser.add_argument('--msg-publish-rate-min-w', help='min warning for metric message_stats.publish.rate', type=float)
    parser.add_argument('--msg-publish-rate-min-c', help='min critical for metric message_stats.publish.rate', type=float)
    parser.add_argument('--msg-publish-rate-max-w', help='max warning for metric message_stats.publish.rate', type=float)
    parser.add_argument('--msg-publish-rate-max-c', help='max critical for metric message_stats.publish.rate', type=float)

    parser.add_argument('--msg-deliver-noack-count-min-w', help='min warning for metric message_stats.deliver_no_ack.count', type=float)
    parser.add_argument('--msg-deliver-noack-count-min-c', help='min critical for metric message_stats.deliver_no_ack.count', type=float)
    parser.add_argument('--msg-deliver-noack-count-max-w', help='max warning for metric message_stats.deliver_no_ack.count', type=float)
    parser.add_argument('--msg-deliver-noack-count-max-c', help='max critical for metric message_stats.deliver_no_ack.count', type=float)
    parser.add_argument('--msg-deliver-noack-rate-min-w', help='min warning for metric message_stats.deliver_no_ack.rate', type=float)
    parser.add_argument('--msg-deliver-noack-rate-min-c', help='min critical for metric message_stats.deliver_no_ack.rate', type=float)
    parser.add_argument('--msg-deliver-noack-rate-max-w', help='max warning for metric message_stats.deliver_no_ack.rate', type=float)
    parser.add_argument('--msg-deliver-noack-rate-max-c', help='max critical for metric message_stats.deliver_no_ack.rate', type=float)

    parser.add_argument('--msg-deliver-get-count-min-w', help='min warning for metric message_stats.deliver_get.count', type=float)
    parser.add_argument('--msg-deliver-get-count-min-c', help='min critical for metric message_stats.deliver_get.count', type=float)
    parser.add_argument('--msg-deliver-get-count-max-w', help='max warning for metric message_stats.deliver_get.count', type=float)
    parser.add_argument('--msg-deliver-get-count-max-c', help='max critical for metric message_stats.deliver_get.count', type=float)
    parser.add_argument('--msg-deliver-get-rate-min-w', help='min warning for metric message_stats.deliver_get.rate', type=float)
    parser.add_argument('--msg-deliver-get-rate-min-c', help='min critical for metric message_stats.deliver_get.rate', type=float)
    parser.add_argument('--msg-deliver-get-rate-max-w', help='max warning for metric message_stats.deliver_get.rate', type=float)
    parser.add_argument('--msg-deliver-get-rate-max-c', help='max critical for metric message_stats.deliver_get.rate', type=float)

    return parser


def rabbitmq_request(config, url):

    host = config.host[:-1]  if config.host.endswith('/')  else config.host 

    if url.startswith('/'):
        url = url[1:]
    
    try:
        r = requests.get(
            'http://{}:{}/{}'.format(host, config.port, url),
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


def parse_overview_metrics(metrics_json):

    metrics = {
        'queue_totals.messages.count': None,
        'queue_totals.messages.rate': None,
        'queue_totals.messages_unacknowledged.count': None,
        'queue_totals.messages_unacknowledged.rate': None,
        'queue_totals.messages_ready.count': None,
        'queue_totals.messages_ready.rate': None,
        'message_stats.publish.count': None,
        'message_stats.publish.rate': None,
        'message_stats.deliver_no_ack.count': None,
        'message_stats.deliver_no_ack.rate': None,
        'message_stats.deliver_get.count': None,
        'message_stats.deliver_get.rate': None,
    }

    if 'queue_totals' in metrics_json  and  metrics_json['queue_totals']:
        metrics['queue_totals.messages.count'] = metrics_json['queue_totals']['messages']
        metrics['queue_totals.messages.rate'] = metrics_json['queue_totals']['messages_details']['rate']

        metrics['queue_totals.messages_unacknowledged.count'] = metrics_json['queue_totals']['messages_unacknowledged']
        metrics['queue_totals.messages_unacknowledged.rate'] = metrics_json['queue_totals']['messages_unacknowledged_details']['rate']

        metrics['queue_totals.messages_ready.count'] = metrics_json['queue_totals']['messages_ready']
        metrics['queue_totals.messages_ready.rate'] = metrics_json['queue_totals']['messages_ready_details']['rate']

    if 'message_stats' in metrics_json  and  metrics_json['message_stats']:
        
        if 'publish' in metrics_json['message_stats']:
            metrics['message_stats.publish.count'] = metrics_json['message_stats']['publish']
      
        if 'publish_details' in metrics_json['message_stats']  and  'rate' in metrics_json['message_stats']['publish_details']:
            metrics['message_stats.publish.rate'] = metrics_json['message_stats']['publish_details']['rate']
      
        if 'deliver_no_ack' in metrics_json['message_stats']:
            metrics['message_stats.deliver_no_ack.count'] = metrics_json['message_stats']['deliver_no_ack']
      
        if 'deliver_no_ack_details' in metrics_json['message_stats']  and  'rate' in metrics_json['message_stats']['deliver_no_ack_details']:
            metrics['message_stats.deliver_no_ack.rate'] = metrics_json['message_stats']['deliver_no_ack_details']['rate']
        
        if 'deliver_get' in metrics_json['message_stats']:
            metrics['message_stats.deliver_get.count'] = metrics_json['message_stats']['deliver_get']
      
        if 'deliver_get_details' in metrics_json['message_stats']  and  'rate' in metrics_json['message_stats']['deliver_get_details']:
            metrics['message_stats.deliver_get.rate'] = metrics_json['message_stats']['deliver_get_details']['rate']

    return metrics


def print_metrics(config, metrics):

    timestamp = int(time.time())
    scheme = config.scheme  if config.scheme is not None  else '{}.rabbitmq'.format(socket.gethostname())

    for k,v in metrics.items():
        if v is not None:
            print( '{}.{} {} {}'.format( scheme, k, v, timestamp))


def check_value(metric_field, metrics, min_w, min_c, max_w, max_c):
    
    is_not_none = lambda x: x is not None
    
    if any(filter(is_not_none, (min_w, min_c, max_w, max_c))):
        
        if metrics.get(metric_field) is None:
            raise SensuChecksException(ERRORCODE_UNKNOWN, "UNKNOWN: no value for metric {}".format(metric_field))

        value = float(metrics[metric_field])

        if ( min_c is not None ) and ( value <= float(min_c) ):
            raise SensuChecksException(ERRORCODE_CRITICAL, "CRITICAL: metric {} = {} is lower or equal than {}".format(metric_field, value, min_c))

        if ( max_c is not None ) and ( value >= float(max_c) ):
            raise SensuChecksException(ERRORCODE_CRITICAL, "CRITICAL: metric {} = {} is higher or equal than {}".format(metric_field, value, max_c))

        if ( min_w is not None ) and ( value <= float(min_w) ):
            raise SensuChecksException(ERRORCODE_WARNING, "WARNING: metric {} = {} is lower or equal than {}".format(metric_field, value, min_w))

        if ( max_w is not None ) and ( value >= float(max_w) ):
            raise SensuChecksException(ERRORCODE_WARNING, "WARNING: metric {} = {} is higher or equal than {}".format(metric_field, value, max_w))

        raise SensuChecksException(ERRORCODE_OK, "metric {} = {}".format(metric_field, value))


def apply_checks(config, metrics):

    check_value(
        'queue_totals.messages.count',
        metrics,
        config.queue_msg_count_min_w,
        config.queue_msg_count_min_c,
        config.queue_msg_count_max_w,
        config.queue_msg_count_max_c,
    )
    check_value(
        'queue_totals.messages.rate',
        metrics,
        config.queue_msg_rate_min_w,
        config.queue_msg_rate_min_c,
        config.queue_msg_rate_max_w,
        config.queue_msg_rate_max_c,
    )
    check_value(
        'queue_totals.messages_unacknowledged.count',
        metrics,
        config.queue_msg_unack_count_min_w,
        config.queue_msg_unack_count_min_c,
        config.queue_msg_unack_count_max_w,
        config.queue_msg_unack_count_max_c,
    )
    check_value(
        'queue_totals.messages_unacknowledged.rate',
        metrics,
        config.queue_msg_unack_rate_min_w,
        config.queue_msg_unack_rate_min_c,
        config.queue_msg_unack_rate_max_w,
        config.queue_msg_unack_rate_max_c,
    )
    check_value(
        'queue_totals.messages_ready.count',
        metrics,
        config.queue_msg_ready_count_min_w,
        config.queue_msg_ready_count_min_c,
        config.queue_msg_ready_count_max_w,
        config.queue_msg_ready_count_max_c,
    )
    check_value(
        'queue_totals.messages_ready.rate',
        metrics,
        config.queue_msg_ready_rate_min_w,
        config.queue_msg_ready_rate_min_c,
        config.queue_msg_ready_rate_max_w,
        config.queue_msg_ready_rate_max_c,
    )
    check_value(
        'message_stats.publish.count',
        metrics,
        config.msg_publish_count_min_w,
        config.msg_publish_count_min_c,
        config.msg_publish_count_max_w,
        config.msg_publish_count_max_c,
    )
    check_value(
        'message_stats.publish.rate',
        metrics,
        config.msg_publish_rate_min_w,
        config.msg_publish_rate_min_c,
        config.msg_publish_rate_max_w,
        config.msg_publish_rate_max_c,
    )
    check_value(
        'message_stats.deliver_no_ack.count',
        metrics,
        config.msg_deliver_noack_count_min_w,
        config.msg_deliver_noack_count_min_c,
        config.msg_deliver_noack_count_max_w,
        config.msg_deliver_noack_count_max_c,
    )
    check_value(
        'message_stats.deliver_no_ack.rate',
        metrics,
        config.msg_deliver_noack_rate_min_w,
        config.msg_deliver_noack_rate_min_c,
        config.msg_deliver_noack_rate_max_w,
        config.msg_deliver_noack_rate_max_c,

    )
    check_value(
        'message_stats.deliver_get.count',
        metrics,
        config.msg_deliver_get_count_min_w,
        config.msg_deliver_get_count_min_c,
        config.msg_deliver_get_count_max_w,
        config.msg_deliver_get_count_max_c,
    )
    check_value(
        'message_stats.deliver_get.rate',
        metrics,
        config.msg_deliver_get_rate_min_w,
        config.msg_deliver_get_rate_min_c,
        config.msg_deliver_get_rate_max_w,
        config.msg_deliver_get_rate_max_c,
    )

    print_metrics(config, metrics)


def main():
    parser = create_parser()
    config = parser.parse_args()
    
    try:
        metrics_json = rabbitmq_request(config, 'api/overview')
        metrics = parse_overview_metrics(metrics_json)
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

