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


class FxNightlyBuild(BuildingMixin, MercurialScript):
    config_options = []

    def __init__(self, require_config_file=True):
        basescript_kwargs = {
            # 'config_options': self.config_options,
            'all_actions': [
                'clobber',
                'pull',
            ],
            # 'default_actions': [],
            'require_config_file': require_config_file,
            # Default configuration
            # 'config': {},
        }
        super(FxNightlyBuild, self).__init__(**basescript_kwargs)

if __name__ == '__main__':
    fx_nightly_build = FxNightlyBuild()
    fx_nightly_build.run_and_exit()
