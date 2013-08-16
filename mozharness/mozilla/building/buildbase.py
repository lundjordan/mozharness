#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""buildbase.py
provides a base class for fx desktop builds

author: Jordan Lund
"""

# import mozharness ;)
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.purge import PurgeMixin


class BuildingMixin(BuildbotMixin, PurgeMixin, object):

    def skip_buildbot_specific_action(self):
        """ignores actions that only should happen within
        buildbot's infrastructure"""
        self.info("This action is specific to buildbot's infrastructure")
        self.info("Skipping......")
        return

    def read_buildbot_config(self):
        c = self.config
        if c.get('developer_run'):
            return self.skip_buildbot_specific_action()
        super(BuildingMixin, self).read_buildbot_config()

    # def check_previous_clobberer_times(self):
    #     """prints history of clobber dates"""
    #     c = self.config
    #     if c.get('developer_run'):
    #         return self.skip_buildbot_specific_action()
    #     # clobberer defined in MercurialScript -> VCSScript -> BaseScript
    #     # since most mozharnesss scripts have a 'clobber' action, let's
    #     # give 'clobberer' a more more explicit name
    #     self.info('made it here')
    #     super(BuildingMixin, self).clobberer()

    def get_clobber_times_and_purge_builds(self):
        """prints history of clobber dates and purge builds"""
        c = self.config
        dirs = self.query_abs_base_dirs()
        if c.get('developer_run'):
            return self.skip_buildbot_specific_action()
        skip = c.get('purge_skip_dirs')
        basedirs = [dirs.get('abs_work_dir'), "/mock/users/cltbld/home/cltbld/build"]

        # purge_builds calls clobberer if 'clobberer_url' in self.config
        super(PurgeMixin, self).purge_builds(skip=skip)
