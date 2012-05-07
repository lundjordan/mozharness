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

import os, sys, platform, shutil

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList
from mozharness.base.vcs.vcsbase import MercurialScript
import logging


# MobileSingleLocale {{{1
class DesktopUnittest(MercurialScript):

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

        #### OS specifics which methods like query_abs_dirs() depends on
        self.OS_name =  None
        self.xpcshell_name = None,
        self.app_name = None,
        self.app_dir = None,
        self.archive_extension = None,
        self.extract_tool = None,
        self.query_OS_specifics()
        #### ############

        MercurialScript.__init__(self,
                config_options=self.config_options,
                all_actions=[
                    # "clobber",
                    # "pull",
                    # "setup",
                    "mochitests",
                    "reftests",
                    "xpcshell",
                    ],
                require_config_file=require_config_file
                )


        self.url_base = None
        self.file_archives = {}
        self.glob_test_options = []
        self.glob_mochi_options = []
        self.xpcshell_options = []


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
            xpcshell_name = 'xpcshell'
            app_name = 'firefox-bin'
            app_dir = 'firefox'
            archive_extension = 'tar.bz2'
            extract_tool = ['tar', '-jxvf']

        elif system == 'Windows':
            if is_64bit:
                OS_name  = 'win64'
            else:
                OS_name = 'win32'
            xpcshell_name = 'xpcshell.exe'
            app_name = 'firefox.exe'
            app_dir = 'firefox'
            archive_extension = 'zip'
            extract_tool = ['unzip', '-o']

        elif system == 'Darwin':
            OS_name =  'macosx64'
            xpcshell_name = 'xpcshell'
            app_name = 'firefox-bin'
            app_dir = './FirefoxNightly.app/Contents/MacOS/firefox-bin'
            archive_extension = 'dmg'
            extract_tool = ['bash' 'tools/buildfarm/utils/installdmg.sh']

        else:
            self.fatal("A supported OS can not be determined")

        self.OS_name =  OS_name,
        self.xpcshell_name = xpcshell_name
        self.app_name = app_name
        self.app_dir = app_dir
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
            symbols_archive = binary_archive.replace(self.archive_extension,
                    'crashreporter-symbols.zip')
        else:
            self.fatal("binary_url was not found in self.config")

        self.file_archives = {
                "binary" : binary_archive,
                "tests" : tests_archive,
                "symbols" : symbols_archive
                }
        return self.file_archives

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs

        c = self.config
        abs_dirs = super(DesktopUnittest, self).query_abs_dirs()
        dirs = {}

        dirs.update(c['dirs'])

        if 'mochitests' in self.actions:
            dirs['abs_mochi_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                    c['dirs']['mochi_dir'])
        if 'reftests' in self.actions:
            dirs['abs_reftest_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                    c['dirs']['reftest_dir'])
        if 'xpcshell' in self.actions:
            dirs['abs_xpcshell_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                    c['dirs']['xpcshell_dir'])

        dirs['abs_app_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                self.app_dir)
        dirs['abs_bin_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                c['dirs']['bin_dir'])
        dirs['abs_tools_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                c['dirs']['tools_dir'])

        dirs['abs_app_plugins_dir'] = os.path.join(dirs['abs_app_dir'], 'plugins')
        dirs['abs_bin_plugins_dir'] = os.path.join(dirs['abs_bin_dir'], 'plugins')
        dirs['abs_app_components_dir'] = os.path.join(dirs['abs_app_dir'], 'components')
        dirs['abs_bin_components_dir'] = os.path.join(dirs['abs_bin_dir'], 'components')

        abs_dirs.update(dirs)

        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_glob_options(self, **kwargs):
        """return a list of options for all tests"""
        if self.glob_test_options:
            return self.glob_test_options

        if kwargs:
            dirs = self.query_abs_dirs()
            glob_test_options  = []
            for key in kwargs.keys():
                kwargs[key] = kwargs[key].format(
                        app_dir=dirs['abs_app_dir'] + '/',
                        app_name=self.app_name,
                        bin_dir=dirs['abs_bin_dir'],
                        symbols_path=self.query_file_archives()['symbols'])
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

    def query_glob_xpcshell_options(self, **kwargs):
        """return a list of options for all tests"""
        if self.xpcshell_options:
            return self.xpcshell_options

        if kwargs:
            xpcshell_options  = []
            for key in kwargs.keys():
                kwargs[key] = kwargs[key].format(
                        symbols_path=self.query_file_archives()['symbols'],
                        xpcshell_name=self.xpcshell_name)
                xpcshell_options.append(kwargs[key])
            self.xpcshell_options = xpcshell_options

            return self.xpcshell_options
        else:
            self.fatal("""No xpcshell options could be found in self.config
                    Please add them to your config file.""")

    def query_specified_suites(self, category):
        """return the suites to run depending on a given category """

        # logic goes: if at least one '--{category}-suite' was given in the script
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

    def copy_tree(self, src, dest, log_level='info', error_level='error'):
        """an implementation of shutil.copytree however it allows
        you to copy to a 'dest' that already exists"""
        self.log("Copying contents from %s to %s" % (src, dest), level=log_level)
        try:
            files = os.listdir(src)
            files.sort()
            for f in files:
                abs_src_f = os.path.join(src, f)
                abs_dest_f = os.path.join(dest, f)
                self.copyfile(abs_src_f , abs_dest_f)
        except (IOError, shutil.Error):
            self.dump_exception("Can't copy %s to %s!" % (src, dest),
                    level=error_level)
            return -1

    def preflight_all_tests(self, OS):
        """preflight commands for all tests if host OS is 'linux' or 'mac'"""
        if 'linux' or 'mac' in OS:
            dirs = self.query_abs_dirs()
            if 'linux' in OS:
                # turn off screensaver
                cmd = ['xset', 's', 'reset']
            else: # mac
                # adjust screen resolution
                cmd = [
                        'bash', '-c', 'screenresolution', 'get', '&&',
                        'screenresolution', 'list', '&&', 'system_profiler',
                        'SPDisplaysDataType'
                        ]
            self.run_command(cmd,
                    cwd=dirs['abs_work_dir'],
                    error_list=MakefileErrorList,
                    halt_on_failure=True)
        else:
            pass


    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists

    def preflight_pull(self):
        """make sure build dir is created since we are not using VCSMixin"""
        dirs = self.query_abs_dirs()
        self.mkdir_p(dirs['abs_work_dir'])

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        url_base = self.query_url_base()
        file_archives = self.query_file_archives()
        repos = c['repos']
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

        #lets clone the tools repo as well
        self.vcs_checkout_repos(repos, parent_dir=dirs['abs_work_dir'])

    def setup(self):
        """extract compressed files"""
        dirs = self.query_abs_dirs()
        bin_archive = self.query_file_archives()['binary']
        tests_archive = self.query_file_archives()['tests']
        extract_binary_cmd = self.extract_tool + [bin_archive]

        self.run_command(extract_binary_cmd,
                cwd=dirs['abs_work_dir'],
                error_list=MakefileErrorList,
                halt_on_failure=True)

        self.run_command(["unzip", "-o", tests_archive],
                cwd=dirs['abs_work_dir'],
                error_list=MakefileErrorList,
                halt_on_failure=True)

    def preflight_mochitests(self):
        self.preflight_all_tests(self.OS_name)

    def mochitests(self):
        """run tests for mochitests"""
        c = self.config
        dirs = self.query_abs_dirs()
        tests_complete = 0

        base_cmd = ["python", dirs["abs_mochi_dir"] + "/runtests.py"]
        glob_test_options = self.query_glob_options(**c['global_test_options'])
        glob_mochi_options = self.query_glob_mochi_options(**c['global_mochi_options'])

        abs_base_cmd = base_cmd + glob_test_options + glob_mochi_options
        mochi_suites = self.query_specified_suites("mochi")

        if mochi_suites :
            for num in range(len(mochi_suites)):
                cmd =  abs_base_cmd + mochi_suites[num]
                print cmd
            #     self.run_command(cmd,
            #             cwd=dirs['abs_work_dir'],
            #             error_list=MakefileErrorList,
            #             halt_on_failure=True)
            # self.info("{0} of {1} tests completed".format(tests_complete,
            #     len(mochi_suites)))
        else:
            self.fatal("""'mochi_suites' could not be determined.
                    If you supplied at least one '--mochitest-suite'
                    when running this script, make sure the value(s) you gave
                    matches the key(s) from 'all_mochi_suites' in your config file.""")


    def preflight_reftests(self):
        self.preflight_all_tests(self.OS_name)

    def reftests(self):
        """run tests for reftests"""
        c = self.config
        dirs = self.query_abs_dirs()
        base_cmd = ["python", dirs["abs_reftest_dir"] + "/runreftest.py"]
        glob_test_options = self.query_glob_options(**c['global_test_options'])
        tests_complete = 0

        abs_base_cmd = base_cmd + glob_test_options
        reftest_suites = self.query_specified_suites("reftest")

        if reftest_suites :
            for num in range(len(reftest_suites)):
                cmd =  abs_base_cmd + reftest_suites[num]
                print cmd
            #     self.run_command(cmd,
            #             cwd=dirs['abs_work_dir'],
            #             error_list=MakefileErrorList,
            #             halt_on_failure=True)
            # self.info("{0} of {1} tests completed".format(tests_complete,
            #     len(reftest_suites)))
        else:
            self.fatal("""'reftest_suites' could not be determined.
                    If you supplied at least one '--reftest-suite'
                    when running this script, make sure the value(s) you gave
                    matches the key(s) from 'all_reftest_suites' in your config file.""")


    def preflight_xpcshell(self):
        self.preflight_all_tests(self.OS_name)

    def xpcshell(self):
        """run tests for xpcshell"""
        c = self.config
        dirs = self.query_abs_dirs()
        app_xpcshell_path = os.path.join(dirs['abs_app_dir'], self.xpcshell_name)
        bin_xpcshell_path = os.path.join(dirs['abs_bin_dir'], self.xpcshell_name)

        base_cmd = ["python", dirs["abs_xpcshell_dir"] + "/runxpcshelltests.py"]
        glob_xpcshell_options = self.query_glob_xpcshell_options(**c['global_xpcshell_options'])
        abs_base_cmd = base_cmd + glob_xpcshell_options

        self.mkdir_p(dirs['abs_app_plugins_dir'])
        self.copyfile(bin_xpcshell_path, app_xpcshell_path)
        self.copy_tree(dirs['abs_bin_components_dir'], dirs['abs_app_components_dir'])
        self.copy_tree(dirs['abs_bin_plugins_dir'], dirs['abs_app_plugins_dir'])

        print abs_base_cmd

        # self.run_command(abs_base_cmd,
        #         cwd=dirs['abs_work_dir'],
        #         error_list=MakefileErrorList,
        #         halt_on_failure=True)
        # self.info("xpcshell test completed")

# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
