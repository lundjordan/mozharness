#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Code to tie into buildbot.
Ideally this will go away if and when we retire buildbot.
"""

import os, re
import pprint
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.config import parse_config_file
from mozharness.base.log import INFO, WARNING, ERROR

# BuildbotMixin {{{1

TBPL_SUCCESS = 'SUCCESS'
TBPL_WARNING = 'WARNING'
TBPL_FAILURE = 'FAILURE'
TBPL_EXCEPTION = 'EXCEPTION'
TBPL_RETRY = 'RETRY'
TBPL_STATUS_DICT = {
    TBPL_SUCCESS: INFO,
    TBPL_WARNING: WARNING,
    TBPL_FAILURE: ERROR,
    TBPL_EXCEPTION: ERROR,
    TBPL_RETRY: WARNING,
}

def create_tinderbox_summary(suite_name, pass_count, fail_count,
        known_fail_count=False, crashed=False, leaked=False):
    emphasize_fail_text = '<em class="testfail">%s</em>'

    if pass_count < 0 or fail_count < 0 or \
            (known_fail_count != None and known_fail_count < 0):
        summary = emphasize_fail_text % 'T-FAIL'
    elif pass_count == 0 and fail_count == 0 and \
            (known_fail_count == None or known_fail_count == 0):
        summary = emphasize_fail_text % 'T-FAIL'
    else:
        str_fail_count = str(fail_count)
        if fail_count > 0:
            str_fail_count = emphasize_fail_text % str_fail_count
        summary = "%d/%s/%d" % (pass_count,
                emphasize_fail_text % str_fail_count, known_fail_count)
    # Format the crash status.
    if crashed:
        summary += "&nbsp;%s" % emphasize_fail_text % "CRASH"
    # Format the leak status.
    if leaked != False:
        summary += "&nbsp;%s" % emphasize_fail_text % (
                (leaked and "LEAK") or "L-FAIL")

    # Return the summary.
    return "TinderboxPrint: %s<br/>%s\n" % (suite_name, summary)

class BuildbotMixin(object):
    buildbot_config = None
    buildbot_properties = {}

    def read_buildbot_config(self):
        c = self.config
        if not c.get("buildbot_json_path"):
            # If we need to fail out, add postflight_read_buildbot_config()
            self.info("buildbot_json_path is not set.  Skipping...")
        else:
            # TODO try/except?
            self.buildbot_config = parse_config_file(c['buildbot_json_path'])
            self.info(pprint.pformat(self.buildbot_config))

    def tryserver_email(self):
        pass

    def buildbot_status(self, tbpl_status, level=None):
        if tbpl_status not in TBPL_STATUS_DICT:
            self.error("buildbot_status() doesn't grok the status %s!" % tbpl_status)
        else:
            if not level:
                level = TBPL_STATUS_DICT[tbpl_status]
            self.add_summary("# TBPL %s #" % tbpl_status, level=level)

    def log_tinderbox_println(self, suite_name, output, full_re_substr, pass_name,
            fail_name, known_fail_name=None):
        """appends 'TinderboxPrint: foo, summary' to the output"""
        full_re = re.compile(full_re_substr)
        harness_errors_re = re.compile(r"TEST-UNEXPECTED-FAIL \| .* \| (Browser crashed \(minidump found\)|missing output line for total leaks!|negative leaks caught!|leaked \d+ bytes during test execution)")
        pass_count, fail_count = -1, -1
        known_fail_count = known_fail_name and -1
        crashed, leaked = False, False

        if str(output) == output:
            output = [output]
        for line in output:
            m = full_re.match(line)
            if m:
                r = m.group(1)
                if r == pass_name:
                    pass_count = int(m.group(2))
                elif r == fail_name:
                    fail_count = int(m.group(2))
                # If otherIdent == None, then totals_re should not match it,
                # so this test is fine as is.
                elif r == known_fail_name:
                    known_fail_count = int(m.group(2))
                continue
            m = harness_errors_re.match(line)
            if m:
                r = m.group(1)
                if r == "Browser crashed (minidump found)":
                    crashed = True
                elif r == "missing output line for total leaks!":
                    leaked = None
                else:
                    leaked = True
                # continue
        print (suite_name, pass_count, fail_count, known_fail_count, crashed, leaked)
        summary = create_tinderbox_summary(suite_name, pass_count, fail_count,
                known_fail_count, crashed, leaked)
        self.info(summary)

    def set_buildbot_property(self, prop_name, prop_value, write_to_file=False):
        self.info("Setting buildbot property %s to %s" % (prop_name, prop_value))
        self.buildbot_properties[prop_name] = prop_value
        if write_to_file:
            return self.dump_buildbot_properties(prop_list=[prop_name], file_name=prop_name)
        return self.buildbot_properties[prop_name]

    def query_buildbot_property(self, prop_name):
        return self.buildbot_properties.get(prop_name)

    def dump_buildbot_properties(self, prop_list=None, file_name="properties", error_level=ERROR):
        c = self.config
        if not os.path.isabs(file_name):
            file_name = os.path.join(c['base_work_dir'], "properties", file_name)
        dir_name = os.path.dirname(file_name)
        if not os.path.isdir(dir_name):
            self.mkdir_p(dir_name)
        if not prop_list:
            prop_list = self.buildbot_properties.keys()
            self.info("Writing buildbot properties to %s" % file_name)
        else:
            if not isinstance(prop_list, (list, tuple)):
                self.log("dump_buildbot_properties: Can't dump non-list prop_list %s!" % str(prop_list), level=error_level)
                return
            self.info("Writing buildbot properties %s to %s" % (str(prop_list), file_name))
        contents = ""
        for prop in prop_list:
            contents += "%s:%s\n" % (prop, self.buildbot_properties.get(prop, "None"))
        return self.write_to_file(file_name, contents)
