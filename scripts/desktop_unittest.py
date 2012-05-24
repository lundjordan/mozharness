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

import os, sys, shutil, copy

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options


# MobileSingleLocale {{{1
class DesktopUnittest(TestingMixin, MercurialScript):

    config_options = [
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
                Examples: 'crashplan', or 'jsreftest'"""
            }
        ],
        [['--disable-preflight-run-commands',],
            {
                "action": "store_true",
                "dest": "preflight_run_commands_disabled",
                "default": True,
                "help": """This will disable any run commands that are specified
                        in the config file under: preflight_run_cmd_suites""",
            }
        ],
    ] + copy.deepcopy(testing_config_options)

    virtualenv_modules = [
     'simplejson',
     {'mozlog': os.path.join('tests', 'mozbase', 'mozlog')},
     {'mozinfo': os.path.join('tests', 'mozbase', 'mozinfo')},
     {'mozhttpd': os.path.join('tests', 'mozbase', 'mozhttpd')},
     {'mozinstall': os.path.join('tests', 'mozbase', 'mozinstall')},
     {'manifestdestiny': os.path.join('tests', 'mozbase', 'manifestdestiny')},
     {'mozprofile': os.path.join('tests', 'mozbase', 'mozprofile')},
     {'mozprocess': os.path.join('tests', 'mozbase', 'mozprocess')},
     {'mozrunner': os.path.join('tests', 'mozbase', 'mozrunner')},
     {'peptest': os.path.join('tests', 'peptest')},
    ]

    def __init__(self, require_config_file=True):

        MercurialScript.__init__(self,
                config_options=self.config_options,
                all_actions=[
                    # 'clobber',
                    # 'read-buildbot-config',
                    # 'create-virtualenv',
                    # 'download-and-extract',
                    # 'pull_other_repos',
                    # 'install',
                    'mochitests',
                    'reftests',
                    'xpcshell',
                    ],
                require_config_file=require_config_file,
                config={'virtualenv_modules': self.virtualenv_modules}
                )

        c = self.config
        self.glob_test_options = []
        self.glob_mochi_options = []
        self.xpcshell_options = []
        self.ran_preflight_run_commands = False
        self.abs_dirs = None

        self.installer_url = c.get('installer_url')
        self.test_url = self.config.get('test_url')
        self.installer_path = c.get('installer_path', self.guess_installer_path())
        self.binary_path = c.get('binary_path')
        self.symbols_url = c.get('symbols_url')


    ###### helper methods


    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(DesktopUnittest, self).query_abs_dirs()
        c = self.config
        dirs = {}
        dirs['abs_app_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'application')

        dirs['abs_app_dir'] = os.path.join(
            dirs['abs_app_install_dir'], 'firefox')
        dirs['abs_app_plugins_dir'] = os.path.join(
            dirs['abs_app_dir'], 'plugins')
        dirs['abs_app_components_dir'] = os.path.join(
            dirs['abs_app_dir'], 'components')

        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_test_bin_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'bin')
        dirs['abs_test_bin_plugins_dir'] = os.path.join(
            dirs['abs_test_bin_dir'], 'plugins')
        dirs['abs_test_bin_components_dir'] = os.path.join(
            dirs['abs_test_bin_dir'], 'components')
        dirs['abs_mochitest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "mochitest")
        dirs['abs_reftest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "reftest")
        dirs['abs_xpcshell_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "xpcshell")
        if os.path.isabs(c['virtualenv_path']):
            dirs['abs_virtualenv_dir'] = c['virtualenv_path']
        else:
            dirs['abs_virtualenv_dir'] = os.path.join(
                abs_dirs['abs_work_dir'],
                c['virtualenv_path'])
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # def query_abs_dirs(self):
    #     if self.abs_dirs:
    #         return self.abs_dirs

    #     c = self.config
    #     abs_dirs = super(DesktopUnittest, self).query_abs_dirs()
    #     dirs = {}

    #     dirs.update(c['dirs'])

    #     if 'mochitests' in self.actions:
    #         dirs['abs_mochi_dir'] = os.path.join(abs_dirs['abs_work_dir'],
    #                 c['dirs']['mochi_dir'])
    #     if 'reftests' in self.actions:
    #         dirs['abs_reftest_dir'] = os.path.join(abs_dirs['abs_work_dir'],
    #                 c['dirs']['reftest_dir'])
    #     if 'xpcshell' in self.actions:
    #         dirs['abs_xpcshell_dir'] = os.path.join(abs_dirs['abs_work_dir'],
    #                 c['dirs']['xpcshell_dir'])

    #     dirs['abs_app_dir'] = os.path.join(abs_dirs['abs_work_dir'],
    #             self.app_dir)
    #     dirs['abs_bin_dir'] = os.path.join(abs_dirs['abs_work_dir'],
    #             c['dirs']['bin_dir'])
    #     dirs['abs_tools_dir'] = os.path.join(abs_dirs['abs_work_dir'],
    #             c['dirs']['tools_dir'])

    #     dirs['abs_app_plugins_dir'] = os.path.join(dirs['abs_app_dir'], 'plugins')
    #     dirs['abs_bin_plugins_dir'] = os.path.join(dirs['abs_bin_dir'], 'plugins')
    #     dirs['abs_app_components_dir'] = os.path.join(dirs['abs_app_dir'], 'components')
    #     dirs['abs_bin_components_dir'] = os.path.join(dirs['abs_bin_dir'], 'components')

    #     abs_dirs.update(dirs)

    #     self.abs_dirs = abs_dirs
    #     return self.abs_dirs

    def guess_installer_path(self):
        """uses regex to guess installer path name based on installer_url.
        Returns None if can't guess or install is in actions(as this will set installer_path"""
        c = self.config
        dirs = self.query_abs_dirs()

        if 'install' in self.actions:
            return None
        elif c.get('installer_url'):
            installer_file_index = c['installer_url'].find('firefox-')
            if installer_file_index != -1:
                installer_path = os.path.join(dirs['abs_work_dir'],
                        c['installer_url'][installer_file_index:])
                self.info('storing installer_path as {0} based upon installer_url'.format(installer_path))
                return installer_path
            else:
                self.fatal("""Could not determine installer_path based on installer_url. Please:
                    (1) verify installer_url path is correct
                    or
                    (2) specify installer_path explicitly with --installer-path instead of --installer-url
                """)

        else:
            self.fatal("installer_url was not found in self.config")

    def _query_symbols_url(self):
        """query the full symbols URL based upon binary URL"""
        # XXX may break with name convention changes but is one less 'input' for script
        if self.symbols_url:
            return self.symbols_url

        installer_url = self.config.get('installer_url')
        symbols_url = None
        self.info("finding symbols_url based upon self.config['installer_url']")
        if installer_url:
            for ext in ['.zip', '.dmg', '.tar.bz2']:
                if ext in installer_url:
                    symbols_url = installer_url.replace(ext, '.crashreporter-symbols.zip')
            if not symbols_url:
                self.fatal("installer_url was found but symbols_url could not be determined")
        else:
            self.fatal("installer_url was not found in self.config")

        self.info("setting symbols_url as {0}".format(symbols_url))
        self.symbols_url = symbols_url
        return self.symbols_url


    def query_glob_options(self, **kwargs):
        """return a list of options for all tests"""
        if self.glob_test_options:
            return self.glob_test_options

        if kwargs:
            dirs = self.query_abs_dirs()
            glob_test_options  = []
            for key in kwargs.keys():
                kwargs[key] = kwargs[key].format(
                        binary_path=self.binary_path,
                        bin_dir=dirs['abs_test_bin_dir'],
                        symbols_path=self._query_symbols_url())
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
        """return a list of options for all xpcshell tests"""
        if self.xpcshell_options:
            return self.xpcshell_options

        if kwargs:
            xpcshell_options  = []
            for key in kwargs.keys():
                xpcshell_options.append(kwargs[key])
            self.xpcshell_options = xpcshell_options

            return self.xpcshell_options
        else:
            self.fatal("""No xpcshell options could be found in self.config
                    Please add them to your config file.""")

    def _query_specified_suites(self, category):
        """return the suites to run depending on a given category"""

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

    def _run_preflight_run_commands(self):
        """preflight commands for all tests"""
        if self.ran_preflight_run_commands:
            pass

        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('preflight_run_commands_disabled'):
            for suite in c['preflight_test_commands']:
                if suite['enabled']:
                    self.info("Running pre test command {name}".format(suite['name']))
                    self.info("Running command " + suite['cmd'])
                    # self.run_command(suite['cmd'],
                    #         cwd=dirs['abs_work_dir'],
                    #         error_list=MakefileErrorList,
                    #         halt_on_failure=True)
            self.ran_preflight_run_commands = True
        else:
            self.warning("""Proceeding without running pretest commands. These are often
                OS specific and disabling them may result in spurious test results!""")


    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists
    # read_buildbot_config is in BuildbotMixin.
    # postflight_read_buildbot_config is in TestingMixin.
    # preflight_download_and_extract is in TestingMixin.
    # download_and_extract is in TestingMixin.
    # create_virtualenv is in VirtualenvMixin.
    # preflight_install is in TestingMixin.
    # install is in TestingMixin.

    def pull_other_repos(self):
        dirs = self.query_abs_dirs()

        if self.config.get('repos'):
            dirs = self.query_abs_dirs()
            self.vcs_checkout_repos(self.config['repos'],
                                    parent_dir=dirs['abs_test_install_dir'])


    def preflight_mochitests(self):
        self._run_preflight_run_commands()

    def mochitests(self):
        """run tests for mochitests"""
        c = self.config
        dirs = self.query_abs_dirs()
        tests_complete = 0

        base_cmd = ["python", dirs["abs_mochitest_dir"] + "/runtests.py"]
        glob_test_options = self.query_glob_options(**c['global_test_options'])
        glob_mochi_options = self.query_glob_mochi_options(**c['global_mochi_options'])

        abs_base_cmd = base_cmd + glob_test_options + glob_mochi_options
        mochi_suites = self._query_specified_suites("mochi")

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
        self._run_preflight_run_commands()

    def reftests(self):
        """run tests for reftests"""
        c = self.config
        dirs = self.query_abs_dirs()
        base_cmd = ["python", dirs["abs_reftest_dir"] + "/runreftest.py"]
        glob_test_options = self.query_glob_options(**c['global_test_options'])
        tests_complete = 0

        abs_base_cmd = base_cmd + glob_test_options
        reftest_suites = self._query_specified_suites("reftest")

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
        self._run_preflight_run_commands()

    def xpcshell(self):
        """run tests for xpcshell"""
        c = self.config
        dirs = self.query_abs_dirs()
        app_xpcshell_path = os.path.join(dirs['abs_app_dir'], c['xpcshell_name'])
        bin_xpcshell_path = os.path.join(dirs['abs_test_bin_dir'], c['xpcshell_name'])

        base_cmd = ["python", dirs["abs_xpcshell_dir"] + "/runxpcshelltests.py"]
        glob_xpcshell_options = self.query_glob_xpcshell_options(**c['global_xpcshell_options'])
        abs_base_cmd = base_cmd + glob_xpcshell_options

        self.mkdir_p(dirs['abs_app_plugins_dir'])
        self.copyfile(bin_xpcshell_path, app_xpcshell_path)
        self.copy_tree(dirs['abs_test_bin_components_dir'], dirs['abs_app_components_dir'])
        self.copy_tree(dirs['abs_test_bin_plugins_dir'], dirs['abs_app_plugins_dir'])

        print abs_base_cmd

        # self.run_command(abs_base_cmd,
        #         cwd=dirs['abs_work_dir'],
        #         error_list=MakefileErrorList,
        #         halt_on_failure=True)
        self.info("xpcshell test completed")

# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
