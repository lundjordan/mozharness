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

    def evaluate_unittest_suite(self, parser, suite_category, suite):
        """parses unittest and adds tinderboxprint summary"""
        result_status = TBPL_SUCCESS
        if parser.num_errors:
            result_status = self.worst_level(TBPL_FAILURE,
                    result_status, levels=TBPL_STATUS_DICT.keys())
        if parser.num_warnings:
            result_status = self.worst_level(TBPL_WARNING,
                    result_status, levels=TBPL_STATUS_DICT.keys())
        if not parser.saved_lines:
            self.add_summary("""No saved_lines of parsed log from suite %s could \
                    be found. These are used for tinderboxprint summaries and \
                    evaluates the (Failed/Unexpected): total count This may \
                    cause inaccurate results""" % suite,
                    level=WARNING)
            return result_status

        result_status = self.eval_lines_and_append_tinderboxprint(suite_category,
                suite, parser.saved_lines, result_status)
        return result_status

    def eval_lines_and_append_tinderboxprint(self, suite_category, suite,
            saved_lines, result_status):
        """This is a base method called from evaluate_unittest_suite. \
        This should be overrided in your script"""
        return self.create_tinderbox_summary() or result_status

    def create_tinderbox_summary(self, suite_name=None, pass_count=None,
            fail_count=None, known_fail_count=False, crashed=False, leaked=False):
        """This is a base method called from eval_lines_and_append_tinderboxprint. \
        This should be overrided in your script"""
        return None

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
