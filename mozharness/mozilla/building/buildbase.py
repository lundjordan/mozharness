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
    'undetermined_repo_path': 'The repo_path could not be determined. \
Please make sure there is a "repo_path" in either your config or a \
buildbot_config.',
    'comments_undetermined': '"comments" could not be determined. This may be \
because it was a forced build.',
    'src_mozconfig_path_not_found': 'The "abs_src_mozconfig" path could not be \
determined. Please make sure it is a valid path \
off of "abs_src_dir"',
    'hg_mozconfig_undetermined': '"hg_mozconfig" could not be determined \
Please add this to your config or else add a local "src_mozconfig" path.',
    'tooltool_manifest_undetermined': '"tooltool_manifest_src" not set, \
Skipping run_tooltool...',
}
ERROR_MSGS.update(MOCK_ERROR_MSGS)


class BuildingMixin(BuildbotMixin, PurgeMixin, MockMixin, SigningMixin,
                    object):

    # in Basescript
def _assert_cfg_valid_for_action(self, dependencies, action):
    """Takes a list of dependencies and ensures that each have an
    assoctiated key in the config. Displays error messages as
    appropriate."""
    # TODO add type and value checking, not just keys 
    # TODO solution should adhere to: bug 699343
    # TODO add this to basescript when the above is done
    c = self.config
    undetermined_keys = []
    err_template = "The key '%s' could not be determined \
and is needed for the action %s. Please add this to your config.\n"
    for dep in dependencies:
        if not c.get(dep):
            undetermined_keys += dep
    if undetermined_keys:
        fatal_msgs = [err_template % (key, action) for key in undetermined_keys]
        self.fatal("".join(fatal_msgs))
    # otherwise:
    return # all good

    def _query_objdir(self):
        if self.objdir:
            return self.objdir

        if not self.config.get('objdir'):
            return self.fatal('The "objdir" could not be determined. '
                              'Please add an "objdir" to your config.')
        self.objdir = self.config['objdir']

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
        old_packages = c.get('old_packages')

        for product in old_packages:
            cmd.append(product % {"objdir": self._query_objdir()})
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
                self.info('abs_src_mozconfig: %s' % (abs_src_mozconfig,))
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
        dirs = self.query_abs_dirs()
        abs_count_ctors_path = os.path.join(dirs['abs_tools_dir'],
                                            'buildfarm/utils/count_ctors.py')
        abs_libxul_path = os.path.join(dirs['abs_src_dir'],
                                       self._query_objdir(),
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

    def _set_build_properties(self):
        """sets buildid, sourcestamp, appVersion, and appName"""
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config/printconfigsetting.py')
        application_ini_path = os.path.join(dirs['abs_src_dir'],
                                            self._query_objdir(),
                                            'dist/bin/application.ini')
        base_cmd = [
            'python', print_conf_setting_path, application_ini_path, 'App'
        ]
        properties_needed = [
            {'ini_name': 'BuildID', 'prop_name': 'buildid'},
            {'ini_name': 'SourceStamp', 'prop_name': 'sourcestamp'},
            {'ini_name': 'Version', 'prop_name': 'appVersion'},
            {'ini_name': 'Name', 'prop_name': 'appName'}
        ]
        for prop in properties_needed:
            prop_val = self.get_output_from_command(
                base_cmd + prop['ini_name'], cwd=dirs['abs_base_dir']
            )
            self.set_buildbot_property(prop['prop_name'],
                                       prop_val,
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
        # 4) what I should probably do, have a separate config for staging /
        # production / preprod ...

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
        gs_pythonpath = os.path.join(dirs['abs_tools_dir'],
                                     'lib',
                                     'python')

        gs_env = self.query_env({'PYTHONPATH': gs_pythonpath})
        branch = self.buildbot_config['properties']['branch']
        resultsname = c['base_name'] % (branch,)
        resultsname = resultsname.replace(' ', '_')
        cmd = ['python', graph_server_post_path]
        cmd.extend(['--server', c['graph_server']])
        cmd.extend(['--selector', c['gragh_selector']])
        cmd.extend(['--branch', self._query_gragh_server_branch_name()])
        cmd.extend(['--buildid', self.buildbot_properties['buildid']])
        cmd.extend(['--sourcestamp', self.buildbot_properties['sourcestamp']])
        cmd.extend(['--resultsname', resultsname])
        cmd.extend(['--properties-file', 'properties.json'])
        cmd.extend(['--timestamp', self.epoch_timestamp])

        self.info("Obtaining graph server post results")
        # TODO buildbot puts this cmd through retry:
        # tools/buildfarm/utils/retry.py -s 5 -t 120 -r 8
        # Find out if I should do the same here
        result_code = self.run_command(cmd,
                                       cwd=dirs['abs_src_dir'],
                                       env=gs_env)
        # TODO find out if this translates to the same from this file:
        # http://mxr.mozilla.org/build/source/buildbotcustom/steps/test.py#73
        if result_code != 0:
            self.error('Automation Error: failed graph server post')
        else:
            self.info("graph server post ok")

    def _set_package_file_properties(self):
        c = self.config
        dirs = self.query_abs_dirs()
        # calls 
        find_dir = os.path.join(dirs['abs_work_dir'],
                                self._query_objdir(),
                                'dist')
        cmd = ["find", find_dir, "-maxdepth", "1", "-type",
               "f", "-name", c['package_filename']]
        package_file_path = self.get_output_from_command(cmd,
                                                         dirs['abs_base_dir'])
        if not package_file_path:
            self.fatal("Can't determine filepath with cmd: %s" % (str(cmd),))

        cmd = ['openssl', 'dgst', '-' + c.get("hash_type", "sha512"),
               package_file_path]
        package_hash = self.get_output_from_command(cmd, dirs['abs_base_dir'])
        if not package_hash:
            self.fatal("undetermined package_hash with cmd: %s" % (str(cmd),))
        self.set_buildbot_property('packageFilename',
                                   os.path.split(package_file_path)[1],
                                   write_to_file=True)
        self.set_buildbot_property('packageSize',
                                   os.path.getsize(package_file_path),
                                   write_to_file=True)
        self.set_buildbot_property('packageHash',
                                   package_hash,
                                   write_to_file=True)

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

    def _do_build_mock_make_cmd(self, cmd, cwd):
        """a similar setup is conducted for many make targets
        throughout a build. This takes a cmd and cwd and calls
        a mock_mozilla with the right env"""
        c = self.config
        env = self.query_env({
            "MOZ_SIGN_CMD": subprocess.list2cmdline(self.query_moz_sign_cmd())
        })
        mock_target = c.get('mock_target')
        if not mock_target:
            return self.fatal(ERROR_MSGS['undetermined_mock_target'])
        self.run_mock_command(mock_target, cmd, cwd=cwd, env=env)

    def build(self):
        """build application"""
        # dependencies in config = ['ccache_env', 'old_packages']
        # see _pre_config_lock
        dirs = self.query_abs_dirs()
        base_cmd = 'make -f client.mk build'
        # TODO, the buildbot_config props buildid
        # after a compile so find out how to get the buildid for here
        buildbot_buildid = self.buildbot_config['properties'].get('buildid',
                                                                  '')
        cmd = base_cmd + ' MOZ_BUILD_DATE=%s' % buildbot_buildid
        self._do_build_mock_make_cmd(cmd, dirs['abs_src_dir'])

    def generate_build_stats(self):
        """this action handles all statitics from a build:
            count_ctors, buildid, sourcestamp, and graph_server_post"""
        if self.config.get('enable_count_ctors'):
            self._count_ctors()
        else:
            self.info("count_ctors not enabled for this build. Skipping...")
        self._set_build_properties()
        if self.config.get('graph_server'):
            self._graph_server_post()
        else:
            num_ctors = self.buildbot_properties.get('num_ctors', 'unknown')
            self.info("TinderboxPrint: num_ctors: %s" % (num_ctors,))

    def make_build_symbols(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('enable_symbols'):
            return self.info('enable_symbols not set. Skipping...')

        cmd = 'make buildsymbols'
        cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        self._do_build_mock_make_cmd(cmd, cwd)

    def make_packages(self):
        c = self.config
        dirs = self.query_abs_dirs()
        # dependencies in config = ['enable_packaging', 'package_filename']
        # see _pre_config_lock
        if not c.get('enable_packaging'):
            return self.info('enable_packaging not set. Skipping...')

        if c.get('enable_package_tests'):
            cmd = 'make package-tests'
            cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
            self._do_build_mock_make_cmd(cmd, cwd)

        cmd = 'make package'
        cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        self._do_build_mock_make_cmd(cmd, cwd)
        # TODO check for if 'rpm' not in self.platform_variation and
        # self.productName not in ('xulrunner', 'b2g'):
        self._set_package_file_properties()

    def make_upload(self):
        c = self.config
        # dependencies in config = ['upload_env', 'stage_platform']
        # see _pre_config_lock
        upload_env = self.query_env(c['upload_env'])
        branch = self.buildbot_config['properties']['branch']
        tinderboxBuildsDir = "%s-%s" % (branch, c['stage_platform'])

        # start here
        uploadArgs = dict(
            upload_dir=tinderboxBuildsDir,
            product=self.stageProduct,
            buildid=WithProperties("%(buildid)s"),
            revision=WithProperties("%(got_revision)s"),
            as_list=False,
        )
# if self.hgHost.startswith('ssh'):
#     uploadArgs['to_shadow'] = True
#     uploadArgs['to_tinderbox_dated'] = False
# else:
#     uploadArgs['to_shadow'] = False
#     uploadArgs['to_tinderbox_dated'] = True
# 
# if self.nightly:
#     uploadArgs['to_dated'] = True
#     if 'st-an' in self.complete_platform or 'dbg' in self.complete_platform or 'asan' in self.complete_platform:
#         uploadArgs['to_latest'] = False
#     else:
#         uploadArgs['to_latest'] = True
#     if self.post_upload_include_platform:
#         # This was added for bug 557260 because of a requirement for
#         # mobile builds to upload in a slightly different location
#         uploadArgs['branch'] = '%s-%s' % (
#             self.branchName, self.stagePlatform)
#     else:
#         uploadArgs['branch'] = self.branchName
# if uploadMulti:
#     upload_vars.append("AB_CD=multi")
# if postUploadBuildDir:
#     uploadArgs['builddir'] = postUploadBuildDir
# uploadEnv['POST_UPLOAD_CMD'] = postUploadCmdPrefix(**uploadArgs)
# 
# if self.productName == 'xulrunner': # XXX TODO this does not get hit
#     self.addStep(RetryingMockProperty(
#                  command=self.makeCmd + ['-f', 'client.mk', 'upload'],
#                  env=uploadEnv,
#                  workdir='build',
#                  extract_fn=parse_make_upload,
#                  haltOnFailure=True,
#                  description=["upload"],
#                  timeout=60 * 60,  # 60 minutes
#                  log_eval_func=lambda c, s: regex_log_evaluator(
#                  c, s, upload_errors),
#                  locks=[upload_lock.access('counting')],
#                  mock=self.use_mock,
#                  target=self.mock_target,
#                  ))
# else: # This is our make upload
#     objdir = WithProperties(
#         '%(basedir)s/' + self.baseWorkDir + '/' + self.objdir)
#     if self.platform.startswith('win'):
#         objdir = '%s/%s' % (self.baseWorkDir, self.objdir)
#     self.addStep(RetryingMockProperty(
#         name='make_upload',
#         command=self.makeCmd + ['upload'] + upload_vars,
#         env=uploadEnv,
#         workdir=objdir,
#         extract_fn=parse_make_upload,
#         haltOnFailure=True,
#         description=self.makeCmd + ['upload'],
#         mock=self.use_mock,
#         target=self.mock_target,
#         mock_workdir_prefix=None,
#         timeout=40 * 60,  # 40 minutes
#         log_eval_func=lambda c, s: regex_log_evaluator(
#             c, s, upload_errors),
#         locks=[upload_lock.access('counting')],
#     ))
