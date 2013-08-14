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
from mozharness.mozilla.building import BuildingMixin
from mozharness.base.script import BaseScript


class FxNightlyBuild(BuildingMixin, BaseScript):
    pass

