#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""desktop_unittest.py

The goal of this is to extract the work from buildbot's factory.py
and run unittests for any Mozilla desktop applictation(my goal
and subject to change upon review

author: Jordan Lund
"""

import os, sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList
from mozharness.base.log import OutputParser
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
                "clobber",
                "wget",
                "setup",
                "mochitests",
                "reftests",
                "xpcshell",
            ],
            require_config_file=require_config_file
        )
        self.buildid = None
        self.make_ident_output = None
        self.version = None
        self.repack_env = None

    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists

    def preflight_wget(self):
        """create build dir"""
        if 'clobber' not in self.actions:
            dirs = self.query_abs_dirs()
            self.mkdir_p(dirs['abs_work_dir'])

    def wget(self):
        c = self.config
        env = self.query_env()
        dirs = self.query_abs_dirs()
        ftp_base = []
        ftp_filenames = []
        zip_count = 0
        version = self.get_output_from_command(
            # TODO Oh my what am I doing? Is there a better way I should do this?
            "wget --quiet -O- http://hg.mozilla.org/{0}/raw-file/default/browser/config/version.txt".format(c['branch']),
            cwd=dirs['abs_work_dir'],
            env=env,
            silent=True
        )
        parser = OutputParser(config=self.config, log_obj=self.log_obj,
                              error_list=MakefileErrorList)
        parser.add_lines(version)

        if False:
            #TODO check if user overrided FTP from config file (ID, version, app, OS)
            ftp_base = "manual ftps"
        else:
            ftp_base = c['ftp_base']
            ftp_filenames = c['ftp_filenames']
        if version:
            for ftp_file in ftp_filenames:
                ftp_file = ftp_file.format(build_version=version.strip())
                import pdb; pdb.set_trace()
                if not self.download_file(ftp_base + "/" + ftp_file, ftp_file, parent_dir=dirs['abs_work_dir']):
                    # could not download the file...
                    self.fatal("Could not download file from {0}".format(ftp_base + "/" + ftp_file))
        else:
            self.fatal("Can't determine version!")

# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
