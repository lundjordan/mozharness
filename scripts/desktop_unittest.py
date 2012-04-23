#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""desktop_unittest.py

The goal of this is to extract the unittestng from buildbot's factory.py
for any Mozilla desktop applictation(my goal
and subject to change upon review)

author: Jordan Lund
"""

import os, sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript

# MobileSingleLocale {{{1
class DesktopUnittest(BaseScript):
    config_options = [[
     ['--release-config-file',],
     {"action": "store",
      "dest": "release_config_file",
      "type": "string",
      "help": "Specify the release config file to use"
     }
     #TODO add more config options like...
     # user ftp override
     # id and version overide
     # app option (firefox, thunderbird, seamonkey, .... mobile?)
     # chunk prefrences
     # close when done
     # autorun
     # and many others I have not looked at
    ]]

    def __init__(self, require_config_file=True):
        BaseScript.__init__(self,
            config_options=self.config_options,
            all_actions=[
                # "clobber",
                "wget",
                "setup",
                "mochitests",
                "reftests",
                "xpcshell",
            ],
            require_config_file=require_config_file
        )
        self.make_ident_output = None
        self.repack_env = None
        self.version = None
        self.ID = None

    # helper methods

    def query_version_and_id(self):
        """find version and ID of application being tested"""
        c = self.config
        dirs = self.query_abs_dirs()
        env = self.query_env()

        if self.version:
            # TODO, check for ID as well instead of hard coding in config file
            return self.version, self.ID

        if False:
            # TODO check for if user overides ID and version
            pass
        else:
            version = self.get_output_from_command(
                # TODO Oh my what am I doing? Is there a better way I should do this?
                "wget --quiet -O- http://hg.mozilla.org/{0}/raw-file/default" +
                "/browser/config/version.txt".format(c['branch']),
                cwd=dirs['abs_work_dir'],
                env=env,
                silent=True
                )
            if version:
                self.version, self.ID = version, None
                return self.version, self.ID
            else:
                self.fatal("Can't determine version!")

    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists

    def preflight_wget(self):
        """make sure build dir is created since we are not using VCSMixin"""
        dirs = self.query_abs_dirs()
        self.mkdir_p(dirs['abs_work_dir'])

    def wget(self):
        c = self.config
        dirs = self.query_abs_dirs()
        ftp_base = c['ftp_base']
        filenames = c['ftp_filenames']
        version, ID = self.query_version_and_id()
        download_count = 0

        for file_name in filenames:
            file_name = file_name.format(build_version=version.strip())
            url = ftp_base + "/" + file_name
            if not self.download_file(url, file_name,
                    parent_dir=dirs['abs_work_dir']):

                self.fatal("Could not download file from {0}".format(url))
            else:
                download_count += 1
        self.info("{0} of {1} files " +
                "downloaded".format(download_count, len(filenames)))

        def setup(self):
            """extract compressed files"""
            pass
            # for file_name in ftp_filenames:

        def mochitests(self):
            """run tests for mochitests"""
            pass

        def reftests(self):
            """run tests for reftests"""
            pass

        def xpcshell(self):
            """run tests for xpcshell"""
            pass






# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
