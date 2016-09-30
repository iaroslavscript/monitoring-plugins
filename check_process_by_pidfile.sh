#!/usr/bin/env bash

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

# sudo permitions are required for the script
# %USERNAME_HERE ALL=(ALL) NOPASSWD:/bin/kill -0 [0-9]*

ERRORCODE_OK=0
ERRORCODE_WARNING=1
ERRORCODE_CRITICAL=2
ERRORCODE_UNKNOWN=3

PATH_PIDFILE=""

function print_help {
    cat<< EOF
Usage: check_process_by_pidfile.sh -f /path/to/pidfile
Checks process by sending kill -0
Required sudo permitions are required for the script:
%USERNAME_HERE ALL=(ALL) NOPASSWD:/bin/kill -0 [0-9]*

LICENSE:
    The MIT License (MIT)
EOF
}



if [ "$#" -lt 2 ]; then
    echo "UNKNOWN: illegal number of parameters"
    print_help
    exit ${ERRORCODE_UNKNOWN}
fi

while getopts ":f:" opt; do
  case $opt in
    f)
      PATH_PIDFILE="$OPTARG"
      ;;
    \?)
      echo "UNKNOWN: Invalid option: -$OPTARG"
      exit ${ERRORCODE_UNKNOWN}
      ;;
    :)
      echo "UNKNOWN: Option -$OPTARG requires an argument."
      exit ${ERRORCODE_UNKNOWN}
      ;;
  esac
done

if [ ! -f "${PATH_PIDFILE}" ]; then
    echo "CRITICAL: file not found ${PATH_PIDFILE}"
    exit ${ERRORCODE_CRITICAL}
fi

error_msg=$(sudo kill -0 $(cat ${PATH_PIDFILE}) 2>&1)

if [ $? -ne 0 ]; then
    echo "CRITICAL: process is not running. Message: $error_msg"
    exit ${ERRORCODE_CRITICAL}
fi

echo "process is running"
exit ${ERRORCODE_OK}

