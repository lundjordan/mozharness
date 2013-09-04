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
import subprocess

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

    # TODO add this / or merge with ToolToolMixin
    def _run_tooltool(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('tooltool_manifest_src'):
            return self.warning(ERROR_MSGS['tooltool_manifest_undetermined'])
        f_and_un_path = os.path.join(dirs['abs_tools_dir'],
                                     'scripts/tooltool/fetch_and_unpack.sh')
        tooltool_manifest_path = os.path.join(dirs['abs_src_dir'],
                                              c['tooltool_manifest_src'])
        cmd = [
            f_and_un_path,
            tooltool_manifest_path,
            c['tooltool_url_list'][0],
            c['tooltool_script'],
            c['tooltool_bootstrap'],
        ]
        self.info(str(cmd))
        self.run_command(cmd, cwd=dirs['abs_src_dir'])

    def _count_ctors(self):
        """count num of ctors and set testresults"""
        c = self.config
        dirs = self.query_abs_dirs()
        abs_count_ctors_path = os.path.join(dirs['abs_tools_dir'],
                                            'buildfarm/utils/count_ctors.py')
        abs_libxul_path = os.path.join(dirs['abs_src_dir'], c.get('objdir'),
                                       'dist/bin/libxul.so')

        cmd = ['python', abs_count_ctors_path, abs_libxul_path]
        self.info(str(cmd))
        output = self.get_output_from_command(cmd, cwd=dirs['abs_src_dir'])
        try:
            output = output.split("\t")
            num_ctors = int(output[0])
            testresults = [(
                'num_ctors', 'num_ctors', num_ctors, str(num_ctors))]
            self.set_buildbot_property('num_ctors',
                                       num_ctors,
                                       write_to_file=True)
            self.set_buildbot_property('testresults',
                                       testresults,
                                       write_to_file=True)
        except:
            self.set_buildbot_property('testresults',
                                       testresults,
                                       write_to_file=True)

    def _set_buildid_and_sourcestamp(self):
        c = self.config
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config/printconfigsetting.py')
        application_ini_path = os.path.join(dirs['abs_src_dir'],
                                            c['objdir'],
                                            'dist/bin/application.ini')
        base_cmd = [
            'python', print_conf_setting_path, application_ini_path, 'App'
        ]
        self.buildid = self.get_output_from_command(base_cmd + 'BuildID',
                                                    cwd=dirs['abs_base_dir'])
        self.sourcestamp = self.get_output_from_command(
            base_cmd + 'SourceStamp', cwd=dirs['abs_base_dir']
        )
        self.set_buildbot_property('buildid',
                                   self.buildid,
                                   write_to_file=True)
        self.set_buildbot_property('sourcestamp',
                                   self.sourcestamp,
                                   write_to_file=True)

    def _query_gragh_server_branch_name(self):
        # XXX TODO not sure if this is what I should do here. We need the
        # graphBranch name which, in misc.py, we define as:
# http://hg.mozilla.org/build/buildbotcustom/file/9620bbcc6485/misc.py#l1167
        # 'graphBranch': config.get('graph_branch',
        #                           config.get('tinderbox_tree', None))
        # from what I can tell, this always relies on tinderbox_tree (not
        # graph_branch) where the logic goes:
        # if we are staging/preproduction (eg: mozilla/staging_config.py)
        #   tinderbox_tree = 'MozillaTest'
        # if we are in production (eg: mozilla/production_config.py)
        #   if branch is 'mozilla-central':
        #       tinderbox_tree = 'Firefox'
        #   else for example say branch is 'mozilla-release':
        #           tinderbox_tree = 'Mozilla-Release'
        # If my logic is right, we have three options. 1) add 'tinderbox_tree'
        # to buildbot_config 2) add a dict to self.config that holds all branch
        # keys and assotiated tinderbox_tree values 3) do what I am doing below

        # XXX not sure if this is the best way to determine staging/preprod
        if 'dev-master' in self.buildbot_config['properties']['master']:
            return 'MozillaTest'

        # XXX more hacky shtuff
        branch = self.buildbot_config['sourcestamp']['branch']
        if branch is 'mozilla-central':
            return 'Firefox'
        else:
            # capitalize every word inbetween '-'
            branch_list = branch.split('-')
            branch_list = [elem.capitalize() for elem in branch_list]
            return '-'.join(branch_list)

    def _graph_server_post(self):
        """graph server post results"""
        c = self.config
        dirs = self.query_abs_dirs()
        graph_server_post_path = os.path.join(dirs['abs_tools_dir'],
                                              'buildfarm',
                                              'utils',
                                              'graph_server_post.py')
        branch = self.buildbot_config['properties']['branch']
        resultsname = c['base_name'] % (branch,)
        resultsname = resultsname.replace(' ', '_')
        cmd = ['python', graph_server_post_path]
        cmd.extend(['--server', c['graph_server']])
        cmd.extend(['--selector', c['gragh_selector']])
        cmd.extend(['--branch', self._query_gragh_server_branch_name()])
        cmd.extend(['--buildid', self.buildid])
        cmd.extend(['--sourcestamp', self.sourestamp])
        cmd.extend(['--resultsname', resultsname])
        cmd.extend(['--properties-file', 'properties.json'])
        cmd.extend(['--timestamp', self.epoch_timestamp])

        self.info("Obtaining graph server post results")
        # TODO buildbot puts this cmd through retry:
        # tools/buildfarm/utils/retry.py -s 5 -t 120 -r 8
        # Find out if I should do the same here
        result_code = self.run_command(cmd, cwd=dirs['abs_src_dir'])
        # TODO find out if this translates to the same from this file:
        # http://mxr.mozilla.org/build/source/buildbotcustom/steps/test.py#73
        if result_code != 0:
            self.error('Automation Error: failed graph server post')
        else:
            self.info("graph server post ok")

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

        if not mock_target:
            self.fatal(MOCK_ERROR_MSGS['undetermined_mock_target'])

        self.reset_mock(mock_target)
        self.init_mock(mock_target)
        if c.get('mock_pre_package_copy_files'):
            self.copy_mock_files(mock_target,
                                 c.get('mock_pre_package_copy_files'))
        for cmd in c.get('mock_pre_package_cmds', []):
            self.run_mock_command(mock_target, cmd, '/')
        if c.get('mock_packages'):
            self.install_mock_packages(mock_target, c.get('mock_packages'))

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

        moz_sign_cmd = subprocess.list2cmdline(self.query_moz_sign_cmd())
        env.update({"MOZ_SIGN_CMD": moz_sign_cmd})
        cmd = 'make -f client.mk build'
        buildbot_buildid = self.buildbot_config['properties'].get('buildid',
                                                                  '')
        cmd = cmd + ' MOZ_BUILD_DATE=%s' % buildbot_buildid
        self.info(str(env))
        self.info(str(cmd))
        self.run_mock_command(mock_target,
                              cmd,
                              cwd=dirs['abs_src_dir'],
                              env=env)

    def generate_build_stats(self):
        self._set_buildid_and_sourcestamp()
        self._graph_server_post()

