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

if [ $# -ne 1 ]; then
    echo "UNKNOWN: illegal number of parameters. Usage: check_process_by_pidfile.sh /path/to/pidfile"
    exit 3
fi

if [ ! -f "$1" ]; then
    echo "CRITICAL: file not found $1"
    exit 2
fi

error_msg=$(sudo kill -0 $(cat $1) 2>&1)

if [ $? -ne 0 ]; then
    echo "CRITICAL: process is not running. Message: $error_msg"
    exit 2
fi

echo "process is running"
exit 0

