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

from mozharness.base.log import WARNING

# ErrorLists {{{1

BaseTestError = [
    {'regex': re.compile(r'''TEST-UNEXPECTED'''), 'level': WARNING,
        'explanation' : "One or more unittests unexpectingly failed. This is a harness error"},
]
CategoryTestErrorList = {
    'mochitest' : BaseTestError  + [
        {'regex': re.compile(r'''(\tFailed: [^0]|\d+ INFO Failed: [^0])'''), 'level': WARNING,
                'explanation' : "One or more unittests failed"},
        ],
    'reftest' : BaseTestError + [
        {'regex': re.compile(r'''^REFTEST INFO \| Unexpected: 0 \('''), 'level': WARNING,
                'explanation' : "One or more unittests failed"},
        ],
    'xpcshell' : BaseTestError + [
        {'regex': re.compile(r'''^INFO \| Failed: 0'''), 'level': WARNING,
                'explanation' : "One or more unittests failed"},
        ],
}
TinderBoxPrint = {
    "mochitest_summary" : {
        'full_re_substr' : r'''(\d+ INFO (Passed|Failed|Todo):\ +(\d+)|\t(Passed|Failed|Todo): (\d+))''',
        'pass_name' : "Passed",
        'fail_name' : "Failed",
        'todo_name' : "Todo",
    },
    "reftest_summary" : {
        'full_re_substr' : r'''REFTEST INFO \| (Successful|Unexpected|Known problems): (\d+) \(''',
        'success_name' : "Successful",
        'pass_name' : "Unexpected",
        'todo_name' : "known problems",
    },
    "xpcshell_summary" : {
        'full_re_substr' : r'''INFO \| (Passed|Failed): (\d+)''',
        'success_name' : "Passed",
        'pass_name' : "Failed",
        'todo_name' : None,
    },
}
