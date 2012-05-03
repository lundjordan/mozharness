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

import os, sys, platform

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList
from mozharness.base.script import BaseScript


# MobileSingleLocale {{{1
class DesktopUnittest(BaseScript):

    config_options = [
        [['--binary-url',],
            {
                "action": "store",
                "dest": "binary_url",
                "type": "string",
                "help": "Specify the release config file to use"
            }
        ],
        [['--mochi-suite',],
            {
                "action" : "append",
                "dest" : "specified_mochi_suites",
                "type": "string",
                "help": """Specify which mochi suite to run.
                Suites are defined in the config file.
                Examples: 'plain1', 'plain5', 'chrome', or 'a11y'"""
            }
        ],

        [['--reftest-suite',],
            {
                "action" : "append",
                "dest" : "specified_reftest_suites",
                "type": "string",
                "help": """Specify which reftest suite to run.
                Suites are defined in the config file.
                Examples: 'plain1', 'plain5', 'chrome', or 'a11y'"""
            }
        ],
    ]

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

        #### OS specifics
        self.OS_name =  None
        self.app_name = None,
        self.archive_extension = None,
        self.extract_tool = None,
        self.query_OS_specifics()
        #### ############

        self.url_base = None
        self.file_archives = None
        self.glob_test_options = []
        self.glob_mochi_options = []


    # helper methods

    def query_OS_specifics(self):
        """return current OS"""
        system = platform.system() #eg 'Darwin', 'Linux', or 'Windows'
        is_64bit = '64' in platform.architecture()[0]

        if system == 'Linux':
            if is_64bit:
                OS_name = 'linux64'
            else:
                OS_name = 'linux'
            app_name = 'firefox'
            archive_extension = 'tar.bz2'
            extract_tool = ['tar', '-jxvf']

        elif system == 'Windows':
            if is_64bit:
                OS_name  = 'win64'
            else:
                OS_name = 'win32'
            app_name = 'firefox.exe'
            archive_extension = 'zip'
            extract_tool = ['unzip', '-o']

        elif system == 'Darwin':
            OS_name =  'macosx64'
            # TODO verify mac app_path, and extract tool/steps
            app_name = 'firefox.app?'
            archive_extension = 'dmg'
            extract_tool = ['hdiutil?']

        else:
            self.fatal("A supported OS can not be determined")

        self.OS_name =  OS_name,
        self.app_name = app_name
        self.archive_extension = archive_extension
        self.extract_tool = extract_tool

    def query_url_base(self):
        """queries full archive filenames needed for all tests"""
        if self.url_base:
            return self.url_base

        c = self.config
        if c.get('binary_url'):
            binary_file_index = c['binary_url'].find('firefox-')
            self.url_base = "http://ftp.mozilla.org/pub/mozilla.org/" + c['binary_url'][0:binary_file_index]
        else:
            self.fatal("binary_url was not found in self.config")
        return self.url_base

    def query_file_archives(self):
        """queries full archive filenames needed for all tests"""
        if self.file_archives:
            return self.file_archives

        c = self.config
        if c.get('binary_url'):
            binary_file_index = c['binary_url'].find('firefox-')
            binary_archive = c['binary_url'][binary_file_index:]
            tests_archive = binary_archive.replace(self.archive_extension, 'tests.zip')
        else:
            self.fatal("binary_url was not found in self.config")

        self.file_archives = {
                "binary" : binary_archive,
                "tests" : tests_archive
                }
        return self.file_archives

    def _query_version(self):
        """find version of application being tested"""
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
                    "wget --quiet -O- http://hg.mozilla.org/{0}".format(c['branch']) +
                    "/raw-file/default/browser/config/version.txt",
                    cwd=dirs['abs_work_dir'],
                    env=env,
                    silent=True
                    )
            if version:
                self.version, self.ID = version, None
                return self.version, self.ID
            else:
                self.fatal("Can't determine version!")

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        c = self.config
        abs_dirs = super(DesktopUnittest, self).query_abs_dirs()
        dirs = {}

        if 'mochitests' in self.actions:
            dirs['abs_mochi_runtest_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                    c['mochi_run_dir'])

        if 'reftests' in self.actions:
            dirs['abs_reftest_runtest_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                    c['reftest_run_dir'])

        # TODO come back to remaining dirs
        # if 'xpcshell' in self.actions and c['firefox_plugins_dir']:
        #     dirs['abs_firefox_plugins_dir'] = os.path.join(abs_dirs['abs_work_dir'],
        #             c['firefox_plugins_dir'])

        abs_dirs.update(dirs)

        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_glob_options(self, **kwargs):
        """return a list of options for all tests"""
        if self.glob_test_options:
            return self.glob_test_options

        if kwargs:
            glob_test_options  = []
            for key in kwargs.keys():
                if key == 'app_path':
                    kwargs[key] = kwargs[key].format(app_name=self.app_name)
                glob_test_options.append(kwargs[key])
            self.glob_test_options = glob_test_options

            return self.glob_test_options
        else:
            self.fatal("""No global test options could be found in self.config
                    Please add them to your config file.""")

    def query_glob_mochi_options(self, **kwargs):
        """return a list of options for all mochi tests"""
        if self.glob_mochi_options:
            return self.glob_mochi_options

        if kwargs:
            glob_test_options  = []
            for key in kwargs.keys():
                glob_test_options.append(kwargs[key])
            self.glob_test_options = glob_test_options

            return self.glob_test_options
        else:
            self.fatal("""No global mochitest options could be found in self.config
                    Please add them to your config file.""")

    def query_specified_suites(self, category):
        """return the suites to run depending on a given category """

        # logic goes: if at least one '--specify-{category}-suite' was given in the script
        # then run only that(those) given suite(s). Else, run all the
        # {category} suites
        c = self.config
        all_suites = c.get('all_{0}_suites'.format(category))
        specified_suites = c.get('specified_{0}_suites'.format(category))
        if specified_suites:
            suites = [all_suites[key] for key in \
                    all_suites.keys() if key in specified_suites]
        else:
            suites = [value for value in all_suites.values()]

        return suites

    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists

    def preflight_wget(self):
        """make sure build dir is created since we are not using VCSMixin"""
        dirs = self.query_abs_dirs()
        self.mkdir_p(dirs['abs_work_dir'])

    def wget(self):
        dirs = self.query_abs_dirs()
        url_base = self.query_url_base()
        file_archives = self.query_file_archives()
        download_count = 0

        for archive in file_archives.values():
            url = url_base + archive
            if not self.download_file(url, archive,
                    parent_dir=dirs['abs_work_dir']):

                self.fatal("Could not download file from {0}".format(url))
            else:
                download_count += 1
        self.info("{0} of {1} files " +
                "downloaded".format(download_count, len(file_archives)))

    def setup(self):
        """extract compressed files"""
        dirs = self.query_abs_dirs()
        bin_archive = self.query_file_archives()["binary"]
        tests_archive = self.query_file_archives()["tests"]
        extract_binary_cmd = self.extract_tool + [bin_archive]

        self.run_command(extract_binary_cmd,
                cwd=dirs['abs_work_dir'],
                error_list=MakefileErrorList,
                halt_on_failure=True)

        self.run_command(["unzip", "-o", tests_archive],
                cwd=dirs['abs_work_dir'],
                error_list=MakefileErrorList,
                halt_on_failure=True)

    def mochitests(self):
        """run tests for mochitests"""
        c = self.config
        dirs = self.query_abs_dirs()
        tests_complete = 0

        run_command = ["python", dirs["abs_mochi_runtest_dir"] + "/runtests.py"]
        glob_test_options = self.query_glob_options(**c['global_test_options'])
        glob_mochi_options = self.query_glob_mochi_options(**c['global_mochi_options'])

        abs_base_command = run_command + glob_test_options + glob_mochi_options
        mochi_suites = self.query_specified_suites("mochi")

        if mochi_suites :
            for num in range(len(mochi_suites)):
                command =  abs_base_command + mochi_suites[num]
                print command
            #     self.run_command(command,
            #             cwd=dirs['abs_work_dir'],
            #             error_list=MakefileErrorList,
            #             halt_on_failure=True)
            # self.info("{0} of {1} tests completed".format(tests_complete,
            #     len(mochi_suites)))
        else:
            self.fatal("""'mochi_suites' could be determined.
                    If you supplied at least one '--mochitest-suite'
                    when running this script, make sure the value(s) you gave
                    matches the key(s) from 'all_mochi_suites' in your config file.""")



    def reftests(self):
        """run tests for reftests"""
        c = self.config
        dirs = self.query_abs_dirs()
        run_command = ["python", dirs["abs_reftest_runtest_dir"] + "/runreftest.py"]
        glob_test_options = self.query_glob_options(**c['global_test_options'])
        tests_complete = 0

        abs_base_command = run_command + glob_test_options
        reftest_suites = self.query_specified_suites("reftest")

        if reftest_suites :
            for num in range(len(reftest_suites)):
                command =  abs_base_command + reftest_suites[num]
                print command
            #     self.run_command(command,
            #             cwd=dirs['abs_work_dir'],
            #             error_list=MakefileErrorList,
            #             halt_on_failure=True)
            # self.info("{0} of {1} tests completed".format(tests_complete,
            #     len(reftest_suites)))
        else:
            self.fatal("""'reftest_suites' could be determined.
                    If you supplied at least one '--reftest-suite'
                    when running this script, make sure the value(s) you gave
                    matches the key(s) from 'all_reftest_suites' in your config file.""")


# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
