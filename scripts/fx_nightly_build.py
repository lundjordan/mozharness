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
                'clobber'
            ],
            # 'default_actions': [],
            'require_config_file': require_config_file,
            # Default configuration
            'config': self.default_config_for_all_platforms(),
        }
        super(FxNightlyBuild, self).__init__(**basescript_kwargs)

    # helpers

    def default_config_for_all_platforms(self):
        """a config dict that is used platform wide, any matching keys within a
        passed in config file (--config-file) will override these keys"""
        clobberer_url = 'http://clobberer.pvt.build.mozilla.org/index.php',

        return {
            # if false, only clobber 'abs_work_dir'
            # if true: possibly clobber, clobberer, and purge_builds
            # see PurgeMixin for clobber() conditions
            'is_automation': True,

            # we wish to clobberer
            'clobberer_url': clobberer_url,
            'periodic_clobber': 168,  # default anyway but can be overwritten

            # we wish to purge builds
            'purge_minsize': 12,
            'purge_skip': ['info', 'rel-*:45d', 'tb-rel-*:45d']
        }


    # Actions {{{2
    # read_buildbot_config in BuildingMixin
    # clobber in BuildingMixin -> PurgeMixin


if __name__ == '__main__':
    fx_nightly_build = FxNightlyBuild()
    fx_nightly_build.run_and_exit()
