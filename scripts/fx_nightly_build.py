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


class FxNightlyBuild(BuildingMixin, MercurialScript, object):
    config_options = [
        [['--developer-run', '--skip-buildbot-actions'], {
            "action": "store_false",
            "dest": "is_automation",
            "default": True,
            "help": "if this is running outside of Mozilla's buildbot"
                    "infrastructure, use this option. It removes actions"
                    "that are not needed."}
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
        # TODO this is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time this should be
        # (seems unnecessary as a script arg: --build-starttime)
        self.epoch_timestamp = time.mktime(datetime.now().timetuple())
        self.repo_path = None
        self.objdir = None
        self.buildid = None
        self.builduid = None
        super(FxNightlyBuild, self).__init__(**basescript_kwargs)

    def _pre_config_lock(self, rw_config):
        """validate that the appropriate config are in self.config for actions
        being run"""
        config_dependencies = {
            # key = action, value = list of action's config dependencies
            'setup-mock': ['mock_target'],
            'build': ['ccache_env', 'old_packages', 'mock_target'],
            'make-build-symbols': ['mock_target'],
            'setup-mock': ['mock_target'],
            'make-packages': [
                'enable_packaging', 'package_filename', 'mock_target'
            ],
            'make-upload': ['upload_env', 'stage_platform', 'make_target'],
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
        clobberer_url = 'http://clobberer.pvt.build.mozilla.org/index.php'

        return {
            # if false, only clobber 'abs_work_dir'
            # if true: possibly clobber, clobberer, and purge_builds
            # see PurgeMixin for clobber() conditions
            'is_automation': True,

            'pgo_build': False,
            'debug_build': False,

            'clobberer_url': clobberer_url,  # we wish to clobberer
            'periodic_clobber': 168,  # default anyway but can be overwritten

            # hg tool stuff
            'default_vcs': 'hgtool',
        }

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
