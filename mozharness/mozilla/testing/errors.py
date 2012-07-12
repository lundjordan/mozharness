#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Mozilla error lists for running tests.

Error lists are used to parse output in mozharness.base.log.OutputParser.

Each line of output is matched against each substring or regular expression
in the error list.  On a match, we determine the 'level' of that line,
whether IGNORE, DEBUG, INFO, WARNING, ERROR, CRITICAL, or FATAL.

"""

import re

from mozharness.base.log import WARNING, ERROR, CRITICAL, FATAL

# ErrorLists {{{1

"global_unittest_error_list" : [
    {'regex': re.compile(r'''TEST-UNEXPECTED'''), 'level': WARNING,
        'explanation' : "This unittest unexpectingly failed. This is a harness error"},
],
"mochitest_error_list" : [
    {'regex': re.compile(r'''(\tFailed: [^0]|\d+ INFO Failed: [^0])'''), 'level': WARNING,
            'explanation' : "1 or more unittests failed"},
],
"reftest_error_list" : [
    {'regex': re.compile(r'''^REFTEST INFO \| Unexpected: 0 \('''), 'level': WARNING,
            'explanation' : "1 or more unittests failed"},
],
"xpcshell_error_list" : [
    {'regex': re.compile(r'''^INFO \| Failed: 0'''), 'level': WARNING,
            'explanation' : "1 or more unittests failed"},
]
BaseErrorList = [
 {'substr': r'''command not found''', 'level': ERROR},
]
