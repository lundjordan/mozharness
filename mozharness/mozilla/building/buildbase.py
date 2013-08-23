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
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.mock import ERROR_MSGS as MOCK_ERROR_MSGS

ERROR_MSGS = {
        'undetermined_ccache_env': 'ccache_env could not be determined. \
Please add this to your config.'
}
ERROR_MSGS.update(MOCK_ERROR_MSGS)


class BuildingMixin(BuildbotMixin, PurgeMixin, MockMixin, object):

    def skip_buildbot_specific_action(self):
        """ignores actions that only should happen within
        buildbot's infrastructure"""
        self.info("This action is specific to buildbot's infrastructure")
        self.info("Skipping......")
        return

    def read_buildbot_config(self):
        c = self.config
        if not c.get('is_automation'):
            return self.skip_buildbot_specific_action()
        super(BuildingMixin, self).read_buildbot_config()

    def setup_mock(self):
        """Overrides mock_setup found in MockMixin.
        Initializes and runs any mock initialization actions.
        Finally, installs packages."""
        if self.done_mock_setup:
            return

        c = self.config
        mock_target = c.get('mock_target')
        mock_pre_package_copy_files = c.get('mock_pre_package_copy_files')
        mock_pre_package_cmds = c.get('mock_pre_package_cmds')
        mock_packages = c.get('mock_packages')

        if not mock_target:
            self.fatal(MOCK_ERROR_MSGS['undetermined_mock_target'])

        self.mock_reset(mock_target)
        self.init_mock(mock_target)
        if mock_pre_package_copy_files:
            self.copy_mock_files(mock_target, mock_pre_package_copy_files)
        if mock_pre_package_cmds:
            for cmd in mock_pre_package_cmds:
                self.run_mock_command(mock_target, cmd, '/')
        if mock_packages:
            self.install_mock_packages(mock_target, mock_packages)

        self.done_mock_setup = True

    def ccache_z(self):
        c = self.config
        dirs = self.query_base_dirs()
        if not c.get('ccache_env'):
            self.fatal(ERROR_MSGS['undetermined_ccache_env'])
        partial_env = c['ccache_env'].format(base_dir=dirs['base_work_dir'])
        ccache_env = self.query_env(partial_env)
        self.run_command(command=['ccache' '-z'],
                         cwd=dirs['work_dir'],
                         env=ccache_env)















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

    # def clobber(self):
    #     """prints history of clobber dates and purge builds"""
    #     c = self.config
    #     dirs = self.query_abs_base_dirs()
    #     if c.get('is_automation'):
    #         return self.skip_buildbot_specific_action()

    #     # purge_builds calls clobberer if 'clobberer_url' in self.config
    #     super(PurgeMixin, self).clobber()
