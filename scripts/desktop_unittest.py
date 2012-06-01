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


# DesktopUnittest {{{1
class DesktopUnittest(TestingMixin, MercurialScript):

    config_options = [
        [['--mochitest-suite',],
            {
                "action" : "append",
                "dest" : "specified_mochitest_suites",
                "type": "string",
                "help": """Specify which mochi suite to run.
                Suites are defined in the config file.
                Examples: 'all', 'plain1', 'plain5', 'chrome', or 'a11y'"""
            }
        ],

        [['--reftest-suite',],
            {
                "action" : "append",
                "dest" : "specified_reftest_suites",
                "type": "string",
                "help": """Specify which reftest suite to run.
                Suites are defined in the config file.
                Examples: 'all', 'crashplan', or 'jsreftest'"""
            }
        ],
        [['--xpcshell-suite',],
            {
                "action" : "append",
                "dest" : "specified_xpcshell_suites",
                "type": "string",
                "help": """Specify which xpcshell suite to run.
                Suites are defined in the config file.
                Examples: 'xpcshell'"""
            }
        ],
        [['--run-all-suites',],
            {
                "action": "store_true",
                "dest": "run_all_suites",
                "default": False,
                "help": """This will run all suites that are specified
                        in the config file. You do not need to specify any other suites.
                        Beware, this may take a while ;)""",
                        }
            ],
        [['--disable-preflight-run-commands',],
            {
                "action": "store_true",
                "dest": "preflight_run_commands_disabled",
                "default": False,
                "help": """This will disable any run commands that are specified
in the config file under: preflight_run_cmd_suites""",
            }
            ],
        # TODO implement --fast option
        [['--fast',],
                {
                    "action": "store_true",
                "dest": "run_fast_suites",
                "default": False,
                "help": """Does nothing ATM but I would like it to run a 'quick' set of test suites to
                see if there are any serious issues that can be noticed immediately.""",
            }
        ],
    ] + copy.deepcopy(testing_config_options)

    # TODO find out which modules I do and dont need here
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
                    'clobber',
                    'read-buildbot-config',
                    'download-and-extract',
                    'pull',
                    'create-virtualenv',
                    'install',
                    'run-tests',
                    ],
                require_config_file=require_config_file,
                config={'virtualenv_modules': self.virtualenv_modules}
                )

        c = self.config
        if not self.check_if_valid_config():
            self.fatal("""Config options are not valid.
                    Please ensure that if the '--run-all-suites' flag was enabled
                    then do not specify to run only specific suites like '--mochitest-suite browser-chrome'""")
        self.global_test_options = []
        self.global_mochi_options = []
        self.suite_categories = ['mochitests', 'reftests', 'xpcshell']
        self.ran_preflight_run_commands = False
        self.abs_dirs = None

        self.installer_url = c.get('installer_url')
        self.test_url = c.get('test_url')
        self.installer_path = c.get('installer_path') or self.guess_installer_path()
        self.binary_path = c.get('binary_path')
        self.symbols_url = c.get('symbols_url')

    ###### helper methods

    def _pre_config_lock(self, rw_config):
        c = self.config
        if not c.get('run_all_suites'):
            return # configs are valid

        is_valid = True
        for category in self.suite_categories:
            specific_suites = c.get('specified_{0}_suites'.format(category))
            if specific_suites:
                if specific_suites != 'all':
                    self.fatal("""Config options are not valid.
                            Please ensure that if the '--run-all-suites' flag was enabled
                            then do not specify to run only specific suites like '--mochitest-suite browser-chrome'""")


    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(DesktopUnittest, self).query_abs_dirs()

        # TODO not make this so ugly
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

    def guess_installer_path(self):
        """uses regex to guess installer_path based on installer_url.
        Returns None if can't guess or the action 'install' is in
        actions(as this will set installer_path)"""
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


    def _query_global_options(self, **kwargs):
        """return a list of options for all tests"""
        if self.global_test_options:
            return self.global_test_options

        if self.binary_path:
            if kwargs:
                dirs = self.query_abs_dirs()
                global_test_options  = []
                for key in kwargs.keys():
                    kwargs[key] = kwargs[key].format(
                            binary_path=self.binary_path,
                            symbols_path=self._query_symbols_url())
                    global_test_options.append(kwargs[key])
                self.global_test_options = global_test_options

                return self.global_test_options
            else:
                self.fatal("""No global test options could be found in self.config
                        Please add them to your config file.""")
        else:
            self.fatal("""the 'appname' or 'binary_path' could not be determined.
            This should be something like '/root/path/with/build/application/firefox/firefox-bin'
            If you are running this script without the 'install' action (where binary_path is set),
            Please make sure you are either:
                    (1) specifing it in the config file under binary_path
                    (2) specifing it on command line with the '--binary-path' flag""")


    def _query_specified_suites(self, category):
        """return the suites to run depending on a given category"""

        # logic goes: if at least one '--{category}-suite' was given in the script
        # then run only that(those) given suite(s). Elif, if no suites were
        # specified and the --run-all-suites flag was given,
        # run all {category} suites. Anything else, run no suites.

        c = self.config
        all_suites = c.get('all_{0}_suites'.format(category))
        specified_suites = c.get('specified_{0}_suites'.format(category))

        suites = None
        if specified_suites:
            if 'all' in specified_suites:
                suites = [value for value in all_suites.values()]
            else:
                suites = [all_suites[key] for key in \
                        all_suites.keys() if key in specified_suites]
        else:
            if c.get('run_all_suites'):
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

    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists
    # read_buildbot_config is in BuildbotMixin.
    # postflight_read_buildbot_config is in TestingMixin.
    # preflight_download_and_extract is in TestingMixin.
    # download_and_extract is in TestingMixin.
    # create_virtualenv is in VirtualenvMixin.
    # preflight_install is in TestingMixin.
    # install is in TestingMixin.

    def pull(self):
        dirs = self.query_abs_dirs()
        c = self.config

        if c.get('repos'):
            dirs = self.query_abs_dirs()
            self.vcs_checkout_repos(c['repos'],
                                    parent_dir=dirs['abs_test_install_dir'])


    def preflight_run_tests(self):
        """preflight commands for all tests"""
        if self.ran_preflight_run_commands:
            return

        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('preflight_run_commands_disabled'):
            for suite in c['preflight_run_cmd_suites']:
                if suite['enabled']:
                    self.info("Running pre test command {name} with '{cmd}'".format(
                        name=suite['name'],
                        cmd=' '.join(suite['cmd'])))
                    self.run_command(suite['cmd'],
                            cwd=dirs['abs_work_dir'],
                            error_list=MakefileErrorList,
                            halt_on_failure=True)
        else:
            self.warning("""Proceeding without running prerun test commands.
            These are often OS specific and disabling them may result in spurious test results!""")

        self.ran_preflight_run_commands = True

    def preflight_xpcshell_run(self):
        c = self.config
        dirs = self.query_abs_dirs()

        self.mkdir_p(dirs['abs_app_plugins_dir'])
        self.copyfile(os.path.join(dirs['abs_test_bin_dir'], c['xpcshell_name']),
            os.path.join(dirs['abs_app_dir'], c['xpcshell_name']))
        self.copy_tree(dirs['abs_test_bin_components_dir'], dirs['abs_app_components_dir'])
        self.copy_tree(dirs['abs_test_bin_plugins_dir'], dirs['abs_app_plugins_dir'])

    def run_tests(self):
        c = self.config
        self._run_category_suites('mochitest', c['global_test_options'],
                category_options=c['global_mochitest_options'])
        self._run_category_suites('reftest', c['global_test_options'])
        self._run_category_suites('misc', c['global_test_options'],
                preflight_run_method=self.preflight_xpcshell_run)

    def _run_category_suites(self, suite_category, global_options,
            category_options=None, preflight_run_method=None):
        """run suite(s) to a specific category"""
        c = self.config
        dirs = self.query_abs_dirs()
        tests_complete = 0
        run_file = c['run_file_name'][suite_category]
        base_cmd = ["python", dirs["abs_%s_dir" % suite_category] + "/" + run_file]
        global_test_options = self._query_global_options(**global_options)

        if category_options:
            global_test_options += category_options

        abs_base_cmd = base_cmd + global_test_options
        suites = self._query_specified_suites(suite_category)

        if preflight_run_method:
            preflight_run_method()

        if suites:
            self.info('#### Running %s suites' % suite_category)
            for num in range(len(suites)):
                cmd =  abs_base_cmd + suites[num]
                self.run_command(cmd,
                        cwd=dirs['abs_work_dir'],
                        error_list=MakefileErrorList,
                        halt_on_failure=True)
            self.info("{0} of {1} tests completed".format(tests_complete,
                len(suites)))


# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
