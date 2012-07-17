#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""desktop_unittest.py

The goal of this is to extract the unittestng from buildbot's factory.py

author: Jordan Lund
"""

import os, sys, copy, platform
import shutil, re

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList, BaseErrorList
from mozharness.mozilla.testing.errors import CategoryTestErrorList
from mozharness.mozilla.testing.errors import TinderBoxPrint
from mozharness.base.log import OutputParser
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.base.log import WARNING
from mozharness.mozilla.buildbot import TBPL_STATUS_DICT


SUITE_CATEGORIES = ['mochitest', 'reftest', 'xpcshell']

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
        ]
    ] + copy.deepcopy(testing_config_options)

    error_list = [
        {'regex': re.compile(r'''^TEST-UNEXPECTED-FAIL'''), 'level': WARNING,
            'explanation' : "this unittest unexpectingly failed. This is a harness error"},
        {'regex': re.compile(r'''^\tFailed: [^0]'''), 'level': WARNING,
               'explanation' : "1 or more unittests failed"},
        {'regex': re.compile(r'''^\d+ INFO Failed: [^0]'''), 'level': WARNING,
                'explanation' : "1 or more unittests failed"},
    ] + PythonErrorList

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
                config={'virtualenv_modules': self.virtualenv_modules,
                        'require_test_zip': True,})

        c = self.config
        self.global_test_options = []
        self.abs_dirs = None

        self.installer_url = c.get('installer_url')
        self.test_url = c.get('test_url')
        self.installer_path = c.get('installer_path')
        self.binary_path = c.get('binary_path')
        self.symbols_url = c.get('symbols_url')
        self.summaries = []

    ###### helper methods

    def _pre_config_lock(self, rw_config):
        c = self.config
        if not c.get('run_all_suites'):
            return # configs are valid

        for category in SUITE_CATEGORIES:
            specific_suites = c.get('specified_%s_suites' % (category))
            if specific_suites:
                if specific_suites != 'all':
                    self.fatal("""Config options are not valid.
Please ensure that if the '--run-all-suites' flag was enabled
then do not specify to run only specific suites like '--mochitest-suite browser-chrome'""")


    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(DesktopUnittest, self).query_abs_dirs()

        c = self.config
        dirs = {}
        dirs['abs_app_install_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'application')

        dirs['abs_app_dir'] = os.path.join(dirs['abs_app_install_dir'], c['app_name_dir'])
        dirs['abs_app_plugins_dir'] = os.path.join(dirs['abs_app_dir'], 'plugins')
        dirs['abs_app_components_dir'] = os.path.join(dirs['abs_app_dir'], 'components')

        dirs['abs_test_install_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_test_bin_dir'] = os.path.join(dirs['abs_test_install_dir'], 'bin')
        dirs['abs_test_bin_plugins_dir'] = os.path.join(dirs['abs_test_bin_dir'],
                'plugins')
        dirs['abs_test_bin_components_dir'] = os.path.join(dirs['abs_test_bin_dir'],
                'components')

        dirs['abs_mochitest_dir'] = os.path.join(dirs['abs_test_install_dir'], "mochitest")
        dirs['abs_reftest_dir'] = os.path.join(dirs['abs_test_install_dir'], "reftest")
        dirs['abs_xpcshell_dir'] = os.path.join(dirs['abs_test_install_dir'], "xpcshell")

        if os.path.isabs(c['virtualenv_path']):
            dirs['abs_virtualenv_dir'] = c['virtualenv_path']
        else:
            dirs['abs_virtualenv_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                c['virtualenv_path'])

        abs_dirs.update(dirs)

        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def _query_symbols_url(self):
        """query the full symbols URL based upon binary URL"""
        # may break with name convention changes but is one less 'input' for script
        if self.symbols_url:
            return self.symbols_url

        symbols_url = None
        self.info("finding symbols_url based upon self.installer_url")
        if self.installer_url:
            for ext in ['.zip', '.dmg', '.tar.bz2']:
                if ext in self.installer_url:
                    symbols_url = self.installer_url.replace(
                            ext, '.crashreporter-symbols.zip')
            if not symbols_url:
                self.fatal("self.installer_url was found but symbols_url could \
                        not be determined")
        else:
            self.fatal("self.installer_url was not found in self.config") 
        self.info("setting symbols_url as %s" % (symbols_url))
        self.symbols_url = symbols_url
        return self.symbols_url

    def _query_abs_base_cmd(self, suite_category):
        if self.binary_path:
            c = self.config
            dirs = self.query_abs_dirs()
            options = []
            run_file = c['run_file_names'][suite_category]
            base_cmd = [self.query_python_path('python')]
            # TODO in buildbot only xpcshell is run with the '-u' (force stdin)
            # flag? should all unittests be run with this in mozharness?
            if suite_category == 'xpcshell':
                base_cmd.append('-u')
            base_cmd.append(dirs["abs_%s_dir" % suite_category] + "/" + run_file)
            str_format_values = {
                'binary_path' : self.binary_path,
                'symbols_path' : self._query_symbols_url()
            }
            if self.config['%s_options' % suite_category]:
                for option in self.config['%s_options' % suite_category]:
                    options.append(option % str_format_values)
                abs_base_cmd = base_cmd + options
                return abs_base_cmd
            else:
                self.warning("""Suite options for %s could not be determined.
If you meant to have options for this suite, please make sure they are specified
in your config under %s_options""" % suite_category, suite_category)
        else:
            self.fatal("""the 'appname' or 'binary_path' could not be determined.
            This should be something like '/root/path/with/build/application/firefox/firefox-bin'
            If you are running this script without the 'install' action (where binary_path is set),
            Please make sure you are either:
                    (1) specifying it in the config file under binary_path
                    (2) specifying it on command line with the '--binary-path' flag""")


    def _query_specified_suites(self, category):
        # logic goes: if at least one '--{category}-suite' was given in the script
        # then run only that(those) given suite(s). Elif, if no suites were
        # specified and the --run-all-suites flag was given,
        # run all {category} suites. Anything else, run no suites.

        c = self.config
        all_suites = c.get('all_%s_suites' % (category))
        specified_suites = c.get('specified_%s_suites' % (category)) # list
        suites = None

        if specified_suites:
            if 'all' in specified_suites:
                # useful if you want a quick way of saying run all suites
                # of a specific category.
                suites = all_suites
            else:
                # suites gets a dict of everything from all_suites where a key
                # is also in specified_suites
                suites = dict((key, all_suites.get(key)) for key in specified_suites \
                        if key in all_suites.keys())
        else:
            if c.get('run_all_suites'): # needed if you dont specify any suites
                suites = all_suites

        return suites

    # this is a new line

    # Actions {{{2

    # clobber defined in BaseScript and deletes mozharness/build if exists
    # read_buildbot_config is in BuildbotMixin.
    # postflight_read_buildbot_config is in TestingMixin.
    # preflight_download_and_extract is in TestingMixin.
    # create_virtualenv is in VirtualenvMixin.
    # preflight_install is in TestingMixin.
    # install is in TestingMixin.

    def download_and_extract(self):
        """
        download and extract test zip / download installer
        optimizes which subfolders to extract from tests zip
        """
        c = self.config
        unzip_tests_dirs = None

        if c['specific_tests_zip_dirs']:
            unzip_tests_dirs = c['minimum_tests_zip_dirs']
            for category in c['specific_tests_zip_dirs'].keys():
                if c['run_all_suites'] or self._query_specified_suites(category) \
                        or 'run-tests' not in self.actions:
                    unzip_tests_dirs.extend(c['specific_tests_zip_dirs'][category])

        if self.test_url:
            self._download_test_zip()
            self._extract_test_zip(target_unzip_dirs=unzip_tests_dirs)
        self._download_installer()

    def pull(self):
        dirs = self.query_abs_dirs()
        c = self.config

        if c.get('repos'):
            dirs = self.query_abs_dirs()
            self.vcs_checkout_repos(c['repos'],
                                    parent_dir=dirs['abs_work_dir'])

    def preflight_run_tests(self):
        """preflight commands for all tests"""
        c = self.config
        dirs = self.query_abs_dirs()

        if not c.get('preflight_run_commands_disabled'):
            for suite in c['preflight_run_cmd_suites']:
                # XXX platform.architecture() may give incorrect values for some
                # platforms like mac as excutable files may be universal
                # files containing multiple architectures
                # NOTE 'enabled' is only here while we have unconsolidated configs
                if suite['enabled'] and \
                        platform.architecture()[0] in suite['architectures']:

                    self.info("Running pre test command %(name)s with '%(cmd)s'" % {
                        'name' : suite['name'],
                        'cmd' : ' '.join(suite['cmd'])})
                    # TODO rather then checking for formatting on every string
                    # in every preflight enabled cmd: find a better solution!
                    # maybe I can implement WithProperties in mozharness?
                    cmd = [x % (self.buildbot_config['properties']) for x in suite['cmd']]
                    self.run_command(cmd,
                            cwd=dirs['abs_work_dir'],
                            error_list=BaseErrorList,
                            halt_on_failure=suite['halt_on_failure'])
        else:
            self.warning("""Proceeding without running prerun test commands.
These are often OS specific and disabling them may result in spurious test results!""")

    def run_tests(self):
        self._run_category_suites('mochitest')
        self._run_category_suites('reftest')
        self._run_category_suites('xpcshell',
                preflight_run_method=self.preflight_xpcshell)

    def preflight_xpcshell(self, suites):
        c = self.config
        dirs = self.query_abs_dirs()

        if suites: # there are xpcshell suites to run
            self.mkdir_p(dirs['abs_app_plugins_dir'])
            self.info('copying %s to %s' % (os.path.join(dirs['abs_test_bin_dir'],
                c['xpcshell_name']), os.path.join(dirs['abs_app_dir'], c['xpcshell_name'])))
            shutil.copy2(os.path.join(dirs['abs_test_bin_dir'], c['xpcshell_name']),
                os.path.join(dirs['abs_app_dir'], c['xpcshell_name']))
            self.copytree(dirs['abs_test_bin_components_dir'],
                    dirs['abs_app_components_dir'], overwrite='update')
            self.copytree(dirs['abs_test_bin_plugins_dir'], dirs['abs_app_plugins_dir'],
                    overwrite='update')

    def _run_category_suites(self, suite_category, preflight_run_method=None):
        """run suite(s) to a specific category"""
        dirs = self.query_abs_dirs()

        abs_base_cmd = self._query_abs_base_cmd(suite_category)
        suites = self._query_specified_suites(suite_category)

        if preflight_run_method:
            preflight_run_method(suites)

        if suites:
            self.info('#### Running %s suites' % suite_category)
            for suite in suites:
                cmd =  abs_base_cmd + suites[suite]
                output = self.get_output_from_command(cmd,
                        cwd=dirs['abs_work_dir'], silent=True)
                # TODO needed to split output line by line to assign write
                # levels but str.split might be slow. Maybe write a generator?
                self._parse_unittest(str.split(output, '\n'), suite_category, suite)
        else:
            self.debug('There were no suites to run for %s' % suite_category)

    def _parse_unittest(self, output, suite_category, suite):
        """parses unittest and adds tinderboxprint summary"""
        c = self.config
        suite_category_error_list = PythonErrorList
        if CategoryTestErrorList.get(suite_category):
            suite_category_error_list += CategoryTestErrorList[suite_category]
        status_levels = TBPL_STATUS_DICT.keys()

        parser = OutputParser(config=c, log_obj=self.log_obj,
                            error_list=suite_category_error_list)
        parser.add_lines(output, status_levels=status_levels)
        result_log_level = TBPL_STATUS_DICT.get(parser.result_status_level,
                parser.result_log_level)

        suite_name = suite_category + '-' + suite
        tbpl = TinderBoxPrint['%s_summary' % suite_category]
        self.log_tinderbox_println(suite_name, output, tbpl['full_re_substr'],
                tbpl['pass_name'], tbpl['fail_name'], tbpl['known_fail_name'])
        self.buildbot_status(parser.result_status_level)

        self.add_summary("The %s suite: %s ran with return status: %s" %
                (suite_category, suite, parser.result_status_level),
                level=result_log_level)


# main {{{1
if __name__ == '__main__':
    desktop_unittest = DesktopUnittest()
    desktop_unittest.run()
