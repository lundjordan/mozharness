#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""fx_nightly_build.py
script harness to build nightly firefox within Mozilla's build environment
and developer machines alike

author: Jordan Lund
"""

import sys
import os
import time
from datetime import datetime

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import mozharness ;)
from mozharness.mozilla.building.buildbase import BuildingMixin
from mozharness.base.vcs.vcsbase import MercurialScript


class FxBuildOptionParser(object):
    """provides a namespace for extending opt parsing for
    fx desktop specsific builds"""
    platform = None
    bits = None

    @classmethod
    def _query_pltfrm_and_bits(cls, target_option, options):
        # this method will inspect the config file path and determine the
        # platform and bits being used. It is for releng configs only

        # let's discover what platform we are using
        if '32' in options.config_files[0]:
            cls.bits = '32'
        elif '64' in options.config_files[0]:
            cls.bits = '64'
        else:
            sys.exit('Could not determine whether to use 32 or 64 bit config. '
                     'Please ensure the "--config-file" has "32" or "64" in'
                     ' it and is specified prior to: %s' % (target_option,))
        # now let's discover what platform we are using
        if 'windows' in options.config_files[0]:
            cls.platform = 'windows'
        elif 'mac' in options.config_files[0]:
            cls.platform = 'mac'
        elif 'linux' in options.config_files[0]:
            cls.platform = 'linux'
        else:
            sys.exit('Could not determine platform being used. Please ensure '
                     'the "--config" has "windows", "mac", or "linux" in'
                     ' it and is specified prior to: %s' % (target_option,))
        return (cls.bits, cls.platform)

    @classmethod
    def set_releng_debug_config(cls, option, opt, value, parser):
        if not cls.bits or not cls.platform:
            bits, pltfrm = cls._query_pltfrm_and_bits(opt, parser.values)

        debug_cfg = 'builds/releng_sub_%s_configs/%s_debug.py' % (pltfrm, bits)
        parser.values.config_files.append(debug_cfg)
        parser.values.using_releng_debug = True


class FxNightlyBuild(BuildingMixin, MercurialScript, object):
    config_options = [
        [['--developer-run', '--skip-buildbot-actions'], {
            "action": "store_false",
            "dest": "is_automation",
            "default": True,
            "help": "If this is running outside of Mozilla's build"
                    "infrastructure, use this option. It ignores actions"
                    "that are not needed and adds config checks."}
         ],
        [['--use-releng-debug-cfg'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_releng_debug_config,
            "dest": "using_releng_debug",
            "default": False,
            "help": "Sets the build to run in debug mode"}
         ],

    ]

    def __init__(self, require_config_file=True):
        basescript_kwargs = {
            'config_options': self.config_options,
            'all_actions': [
                'read-buildbot-config',
                'clobber',
                'pull',
                'setup-mock',
                'checkout-source',
                'build',
                'generate-build-properties',
                'generate-build-stats',
                'make-build-symbols',
                'make-packages',
                'make-upload',
                'test-pretty-names',
                'check-test-complete',
                'enable-ccache',
            ],
            'require_config_file': require_config_file,
            # Default configuration
            'config': self.default_config_for_all_platforms(),
        }
        # TODO epoch is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time this should be
        # (seems unnecessary as a script arg: --build-starttime)
        self.epoch_timestamp = int(time.mktime(datetime.now().timetuple()))
        self.repo_path = None
        self.objdir = None
        self.buildid = None
        self.builduid = None
        super(FxNightlyBuild, self).__init__(**basescript_kwargs)

    def _pre_config_lock(self, rw_config):
        """First, validate that the appropriate config are in self.config
        for actions being run. Then resolve optional config files
        (if any)."""

        ### verify config options are valid
        # if not c['is_automation'] (ie: we are outside releng infra)
        # lets make sure we haven't accidently added a releng config
        c = self.config
        if not c['is_automation']:
            releng_configs_used = []
            if c.get('using_releng_debug'):
                releng_configs_used.append('--use-releng-debug-cfg')

            for cfg in releng_configs_used:
                self.warning("You're using a config that is specific to a \
Mozilla build machine by running this script with the option: %s" % (cfg,))
            if releng_configs_used:
                self.fatal("If you're using a machine from our moz build infra"
                           ", please remove the option: '--developer-run'.")

        # now verify config keys are valid for actions being used this run
        config_dependencies = {
            # key = action, value = list of action's config dependencies
            'setup-mock': ['mock_target'],
            'build': ['ccache_env', 'old_packages', 'mock_target'],
            'generate-build-stats': [
                'graph_server', 'graph_selector',
                'graph_branch', 'base_name'
            ],
            'make-build-symbols': ['mock_target'],
            'setup-mock': ['mock_target'],
            'make-packages': ['package_filename', 'mock_target'],
            'make-upload': ['upload_env', 'stage_platform', 'mock_target'],
            'test-pretty-names': ['pretty_name_pkg_targets',
                                  'l10n_check_test'],
        }
        for action in self.actions:
            if config_dependencies.get(action):
                self._assert_cfg_valid_for_action(config_dependencies[action],
                                                  action)

    # helpers

    def default_config_for_all_platforms(self):
        """a config dict that is used platform wide, any matching keys within a
        passed in config file (--config-file) will override these keys"""
        return {}

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(FxNightlyBuild, self).query_abs_dirs()

        dirs = {
            'abs_src_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'mozilla-central'),
            'abs_tools_dir': os.path.join(abs_dirs['abs_work_dir'], 'tools'),
        }
        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # Actions {{{2
    # read_buildbot_config in BuildingMixin
    # clobber in BuildingMixin -> PurgeMixin
    # if Linux config:
        # reset_mock in BuildingMixing -> MockMixin
        # setup_mock in BuildingMixing (overrides MockMixin.mock_setup)


if __name__ == '__main__':
    fx_nightly_build = FxNightlyBuild()
    fx_nightly_build.run_and_exit()
