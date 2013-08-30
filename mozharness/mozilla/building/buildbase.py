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

import os

# import the power of mozharness ;)
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.signing import SigningMixin
from mozharness.mozilla.mock import ERROR_MSGS as MOCK_ERROR_MSGS

ERROR_MSGS = {
    'undetermined_ccache_env': 'ccache_env could not be determined. \
Please add this to your config.',
    'undetermined_old_package': 'The old package could not be determined. \
Please add an "objdir" and "old_packages" to your config.',
    'undetermined_repo_path': 'The repo_path could not be determined. \
Please make sure there is a "repo_path" in either your config or a \
buildbot_config.',
    'src_mozconfig_path_not_found': 'The "src_mozconfig" path could not be \
determined. Please add this to your config and make sure it is a valid path \
off of "abs_src_dir"',
    'hg_mozconfig_undetermined': '"hg_mozconfig" could not be determined \
Please add this to your config or else add a local "src_mozconfig" path.',
    'comments_undetermined': '"comments" could not be determined. This may be \
because it was a forced build.',
    'tooltool_manifest_undetermined': '"tooltool_manifest_src" not set, \
Skipping run_tooltool...'

}
ERROR_MSGS.update(MOCK_ERROR_MSGS)


class BuildingMixin(BuildbotMixin, PurgeMixin, MockMixin, SigningMixin,
                    object):

    # TODO query_repo is basically a copy from B2GBuild, maybe get B2GBuild to
    # inherit from BuildingMixin after buildbase's generality is more defined?
    def _query_repo(self):
        if self.repo_path:
            return self.repo_path

        repo_path = ''
        if self.buildbot_config and 'properties' in self.buildbot_config:
            bbot_repo = self.buildbot_config['properties'].get('repo_path')
            repo_path = 'http://hg.mozilla.org/%s' % (bbot_repo,)
        else:
            repo_path = self.config.get('repo')
        if not repo_path:
            self.fatal(ERROR_MSGS['undetermined_repo_path'])
        self.repo_path = repo_path
        return self.repo_path

    def _skip_buildbot_specific_action(self):
        """ignores actions that only should happen within
        buildbot's infrastructure"""
        self.info("This action is specific to buildbot's infrastructure")
        self.info("Skipping......")
        return

    def _ccache_z(self):
        """clear ccache stats"""
        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('ccache_env'):
            self.fatal(ERROR_MSGS['undetermined_ccache_env'])

        c['ccache_env']['CCACHE_BASEDIR'] = c['ccache_env'].get(
            'CCACHE_BASEDIR', "") % {"base_dir": dirs['base_work_dir']}
        ccache_env = self.query_env(c['ccache_env'])
        self.run_command(command=['ccache', '-z'],
                         cwd=dirs['abs_work_dir'],
                         env=ccache_env)

    def _rm_old_package(self):
        """rm the old package"""
        c = self.config
        cmd = ["rm", "-rf"]
        objdir = c.get('objdir')
        old_packages = c.get('old_packages')
        if not objdir or not old_packages:
            self.fatal(ERROR_MSGS['undetermined_old_package'])

        for product in old_packages:
            cmd.append(product % {"objdir": objdir})
        self.info("removing old packages...")
        self.run_command(cmd, cwd=self.query_abs_dirs()['abs_work_dir'])

    def _get_mozconfig(self):
        """assigns mozconfig"""
        c = self.config
        dirs = self.query_abs_dirs()
        if c.get('src_mozconfig'):
            self.info('Using in-tree mozconfig')
            abs_src_mozconfig = os.path.join(dirs['abs_src_dir'],
                                             c.get('src_mozconfig'))
            if not os.path.exists(abs_src_mozconfig):
                self.fatal(ERROR_MSGS['src_mozconfig_path_not_found'])
            self.copyfile(abs_src_mozconfig,
                          os.path.join(dirs['abs_src_dir'], '.mozconfig'))
        else:
            self.info('Downloading mozconfig')
            hg_mozconfig_url = c.get('hg_mozconfig')
            if not hg_mozconfig_url:
                self.fatal(ERROR_MSGS['hg_mozconfig_undetermined'])
            self.download_file(hg_mozconfig_url,
                               '.mozconfig',
                               dirs['abs_src_dir'])
        self.run_command(['cat', '.mozconfig'], cwd=dirs['abs_src_dir'])

    def _run_tooltool(self):
        c = self.config
        dirs = self.query_abs_dirs
        if not c.get('tooltool_manifest_src'):
            return self.warning(ERROR_MSGS['tooltool_manifest_undetermined'])
        f_and_un_path = os.join.path(dirs['abs_tools_dir'],
                                     'scripts/tooltool/fetch_and_unpack.sh')
        cmd = [
            f_and_un_path,
            c['tooltool_manifest_src'],
            c['tooltool_url_list'],
            c['tooltool_script'],
            c['tooltool_bootstrap'],
        ]
        self.run_command(cmd, cwd=dirs['abs_src_dir'])

    def read_buildbot_config(self):
        c = self.config
        if not c.get('is_automation'):
            return self._skip_buildbot_specific_action()
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

        self.reset_mock(mock_target)
        self.init_mock(mock_target)
        if mock_pre_package_copy_files:
            self.copy_mock_files(mock_target, mock_pre_package_copy_files)
        if mock_pre_package_cmds:
            for cmd in mock_pre_package_cmds:
                self.run_mock_command(mock_target, cmd, '/')
        if mock_packages:
            self.install_mock_packages(mock_target, mock_packages)

        self.done_mock_setup = True

    def checkout_source(self):
        """use vcs_checkout to grab source needed for build"""
        c = self.config
        dirs = self.query_abs_dirs()
        repo = self._query_repo()
        rev = self.vcs_checkout(repo=repo, dest=dirs['abs_src_dir'])
        if c.get('is_automation'):
            changes = self.buildbot_config['sourcestamp']['changes']
            if changes:
                comments = changes[0].get('comments', '')
                self.set_buildbot_property('comments',
                                           comments,
                                           write_to_file=True)
            else:
                self.warning(ERROR_MSGS['comments_undetermined'])
            self.set_buildbot_property('got_revision', rev, write_to_file=True)

    def preflight_build(self):
        """set up machine state for a complete build"""
        c = self.config
        if c.get('enable_ccache'):
            self._ccache_z()
        self._rm_old_package()
        self._get_mozconfig()
        self._run_tooltool()

    def build(self):
        """build application"""
        c = self.config
        env = self.query_env()
        dirs = self.query_abs_dirs()
        mock_target = c.get('mock_target')

        env.update("MOZ_SIGN_CMD": self.query_moz_sign_cmd())
        cmd = ['make', '-f', 'client.mk', 'build']
        self.run_mock_command(mock_target,
                              cmd,
                              cwd=dirs['abs_src_dir'],
                              env=env)
