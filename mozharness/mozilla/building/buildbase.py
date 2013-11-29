#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" buildbase.py.

provides a base class for fx desktop builds
author: Jordan Lund

"""

import os
import subprocess
import re
import time
import uuid

# import the power of mozharness ;)
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.signing import SigningMixin
from mozharness.mozilla.mock import ERROR_MSGS as MOCK_ERROR_MSGS
from mozharness.base.log import OutputParser
from mozharness.mozilla.buildbot import TBPL_RETRY
from mozharness.mozilla.testing.unittest import tbox_print_summary
from mozharness.mozilla.testing.errors import TinderBoxPrintRe

TBPL_UPLOAD_ERRORS = [
    {
        'regex': re.compile("Connection timed out"),
        'level': TBPL_RETRY,
    },
    {
        'regex': re.compile("Connection reset by peer"),
        'level': TBPL_RETRY,
    },
    {
        'regex': re.compile("Connection refused"),
        'level': TBPL_RETRY,
    }
]


ERROR_MSGS = {
    'undetermined_repo_path': 'The repo_path could not be determined. \
Please make sure there is a "repo_path" in either your config or a \
buildbot_config.',
    'comments_undetermined': '"comments" could not be determined. This may be \
because it was a forced build.',
    'src_mozconfig_path_not_found': '"abs_src_mozconfig" path could not be \
determined. Please make sure it is a valid path \
off of "abs_src_dir"',
    'hg_mozconfig_undetermined': '"hg_mozconfig" could not be determined \
Please add this to your config or else add a local "src_mozconfig" path.',
    'tooltool_manifest_undetermined': '"tooltool_manifest_src" not set, \
Skipping run_tooltool...',
}
ERROR_MSGS.update(MOCK_ERROR_MSGS)

### Output Parsers


class MakeUploadOutputParser(OutputParser):
    tbpl_error_list = TBPL_UPLOAD_ERRORS

    def __init__(self, **kwargs):
        self.matches = {}
        super(MakeUploadOutputParser, self).__init__(**kwargs)

    def parse_single_line(self, line):
        pat = r'''^(https?://.*?\.(?:tar\.bz2|dmg|zip|apk|rpm|mar|tar\.gz))$'''
        m = re.compile(pat).match(line)
        if m:
            m = m.group(1)
            # let's create a switch case using name-spaces/dict
            # rather than a long if/else with duplicate code
            property_conditions = {
                # key: property name, value: condition
                'develRpmUrl': "'devel' in m and m.endswith('.rpm')",
                'testsRpmUrl': "'tests' in m and m.endswith('.rpm')",
                'packageRpmUrl': "m.endswith('.rpm')",
                'symbolsUrl': "m.endswith('crashreporter-symbols.zip') or "
                              "m.endswith('crashreporter-symbols-full.zip')",
                'testsUrl': "m.endswith(('tests.tar.bz2', 'tests.zip'))",
                'unsignedApkUrl': "m.endswith('apk') and "
                                  "'unsigned-unaligned' in m",
                'robocopApkUrl': "m.endswith('apk') and 'robocop' in m",
                'jsshellUrl': "'jsshell-' in m and m.endswith('.zip')",
                'completeMarUrl': "m.endswith('.complete.mar')",
                'partialMarUrl': "m.endswith('.mar') and '.partial.' in m",
            }
            for prop, condition in property_conditions.iteritems():
                prop_assigned = False
                if eval(condition):
                    self.matches[prop] = m
                    prop_assigned = True
                    break
            if not prop_assigned:
                # if we found a match but havn't identified the prop then this
                # is the packageURL. Let's consider this the else block
                self.matches['packageUrl'] = m

        # now let's check for retry errors which will give log levels:
        # tbpl status as RETRY and mozharness status as WARNING
        for error_check in self.tbpl_error_list:
            if error_check['regex'].search(line):
                self.num_warnings += 1
                self.warning(line)
                self.buildbot_status(error_check['level'])
                break
        else:
            self.info(line)


class CheckTestCompleteParser(OutputParser):
    tbpl_error_list = TBPL_UPLOAD_ERRORS

    def __init__(self, **kwargs):
        self.matches = {}
        super(CheckTestCompleteParser, self).__init__(**kwargs)
        self.pass_count = 0
        self.fail_count = 0
        self.leaked = False
        self.harnessErrRe = TinderBoxPrintRe['harness_error']['full_regex']

    def parse_single_line(self, line):
        # Counts and flags.
        # Regular expression for crash and leak detections.
        if "TEST-PASS" in line:
            self.pass_count += 1
            return self.info(line)
        if "TEST-UNEXPECTED-" in line:
            # Set the error flags.
            # Or set the failure count.
            m = self.harnessErrRe.match(line)
            if m:
                r = m.group(1)
                if r == "missing output line for total leaks!":
                    self.leaked = None
                else:
                    self.leaked = True
            else:
                self.fail_count += 1
            return self.warning(line)
        self.info(line)  # else

    def evaluate_parser(self):
        # Return the summary.
        summary = tbox_print_summary(self.pass_count,
                                     self.fail_count,
                                     self.leaked)
        self.info("TinderboxPrint: check<br/>%s\n" % (summary))

#### Mixins


class BuildingMixin(BuildbotMixin, PurgeMixin, MockMixin, SigningMixin,
                    object):

    objdir = None
    repo_path = None
    buildid = None
    builduid = None

    def _assert_cfg_valid_for_action(self, dependencies, action):
        """ assert dependency keys are in config for given action.

        Takes a list of dependencies and ensures that each have an
        assoctiated key in the config. Displays error messages as
        appropriate.

        """
        # TODO add type and value checking, not just keys
        # TODO solution should adhere to: bug 699343
        # TODO add this to basescript when the above is done
        c = self.config
        undetermined_keys = []
        err_template = "The key '%s' could not be determined \
and is needed for the action '%s'. Please add this to your config \
or run without that action (ie: --no-{action})"
        for dep in dependencies:
            if not c.get(dep):
                undetermined_keys.append(dep)
        if undetermined_keys:
            fatal_msgs = [err_template % (key, action)
                          for key in undetermined_keys]
            self.fatal("".join(fatal_msgs))
        # otherwise:
        return  # all good

    def query_builduid(self):
        if self.builduid:
            return self.builduid
        if self.buildbot_config['properties'].get('buildid'):
            self.builduid = self.buildbot_config['properties']['buildid']
        else:
            self.builduid = uuid.uuid4().hex
            self.set_buildbot_property('builduid',
                                       self.builduid,
                                       write_to_file=True)
        return self.builduid

    def query_buildid(self):
        if self.buildid:
            return self.buildid
        if self.buildbot_config['properties'].get('buildid'):
            self.buildid = self.buildbot_config['properties']['builduid']
        else:
            self.buildid = time.strftime("%Y%m%d%H%M%S",
                                         time.localtime(time.time()))
            self.set_buildbot_property('buildid',
                                       self.buildid,
                                       write_to_file=True)
        return self.buildid

    def _query_objdir(self):
        if self.objdir:
            return self.objdir

        if not self.config.get('objdir'):
            return self.fatal('The "objdir" could not be determined. '
                              'Please add an "objdir" to your config.')
        self.objdir = self.config['objdir']
        return self.objdir

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
        """ ignore actions from buildbot's infra."""
        self.info("This action is specific to buildbot's infrastructure")
        self.info("Skipping......")
        return

    def query_env(self):
        c = self.config
        env = super(BuildingMixin, self).query_env()
        if self.query_is_nightly():
            env["IS_NIGHTLY"] = "yes"
            if c["create_snippets"] and c['platform_supports_snippets']:
                # in branch_specifics.py we might set update_channel explicitly
                if c.get('update_channel'):
                    env["MOZ_UPDATE_CHANNEL"] = c['update_channel']
                else:  # let's just give the generic channel based on branch
                    env["MOZ_UPDATE_CHANNEL"] = "nightly-%s" % (self.branch,)
        return env

    def _ccache_z(self):
        """clear ccache stats."""
        c = self.config
        dirs = self.query_abs_dirs()

        c['ccache_env']['CCACHE_BASEDIR'] = c['ccache_env'].get(
            'CCACHE_BASEDIR', "") % {"base_dir": dirs['base_work_dir']}
        ccache_env = self.query_env()
        ccache_env.update(c['ccache_env'])
        self.run_command(command=['ccache', '-z'],
                         cwd=dirs['abs_src_dir'],
                         env=ccache_env)

    def _rm_old_package(self):
        """rm the old package."""
        c = self.config
        cmd = ["rm", "-rf"]
        old_packages = c.get('old_packages')

        for product in old_packages:
            cmd.append(product % {"objdir": self._query_objdir()})
        self.info("removing old packages...")
        self.run_command(cmd, cwd=self.query_abs_dirs()['abs_src_dir'])

    def _rm_old_symbols(self):
        cmd = [
            "find", "20*", "-maxdepth", "2", "-mtime", "+7", "-exec", "rm",
            "-rf", "{}", "';'"
        ]
        self.info("removing old symbols...")
        self.run_command(cmd, cwd=self.query_abs_dirs()['abs_work_dir'])

    def _do_build_mock_make_cmd(self, cmd, cwd, env=None, **kwargs):
        """run make cmd against mock.

        make a similar setup is conducted for many make targets
        throughout a build. This takes a cmd and cwd and calls
        a mock_mozilla with the right env

        """
        c = self.config
        if not env:
            env = self.query_env()
            if c['enable_signing']:
                moz_sign_cmd = self.query_moz_sign_cmd()
                env.update({
                    "MOZ_SIGN_CMD": subprocess.list2cmdline(moz_sign_cmd)
                })
        mock_target = c.get('mock_target')
        self.run_mock_command(mock_target, cmd, cwd=cwd, env=env, **kwargs)

    def _get_mozconfig(self):
        """assign mozconfig."""
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
            hg_mozconfig_url = c.get('hg_mozconfig') % (self.branch,)
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
        """count num of ctors and set testresults."""
        dirs = self.query_abs_dirs()
        testresults = []
        abs_count_ctors_path = os.path.join(dirs['abs_tools_dir'],
                                            'buildfarm/utils/count_ctors.py')
        abs_libxul_path = os.path.join(dirs['abs_src_dir'],
                                       self._query_objdir(),
                                       'dist/bin/libxul.so')

        cmd = ['python', abs_count_ctors_path, abs_libxul_path]
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

    def _query_graph_server_branch_name(self):
        c = self.config
        if c.get('graph_server_branch_name'):
            return c['graph_server_branch_name']
        else:
            # capitalize every word inbetween '-'
            branch_list = self.branch.split('-')
            branch_list = [elem.capitalize() for elem in branch_list]
            return '-'.join(branch_list)

    def _graph_server_post(self):
        """graph server post results."""
        c = self.config
        dirs = self.query_abs_dirs()
        graph_server_post_path = os.path.join(dirs['abs_tools_dir'],
                                              'buildfarm',
                                              'utils',
                                              'graph_server_post.py')
        gs_pythonpath = os.path.join(dirs['abs_tools_dir'],
                                     'lib',
                                     'python')

        gs_env = self.query_env()
        gs_env.update({'PYTHONPATH': gs_pythonpath})
        resultsname = c['base_name'] % {'branch': self.branch}
        cmd = ['python', graph_server_post_path]
        cmd.extend(['--server', c['graph_server']])
        cmd.extend(['--selector', c['graph_selector']])
        cmd.extend(['--branch', self._query_graph_server_branch_name()])
        cmd.extend(['--buildid', self.query_buildbot_property('buildid')])
        cmd.extend(['--sourcestamp',
                    self.query_buildbot_property('sourcestamp')])
        cmd.extend(['--resultsname', resultsname])
        cmd.extend(['--testresults',
                    str(self.query_buildbot_property('testresults'))])
        cmd.extend(['--timestamp', str(self.epoch_timestamp)])

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
        find_dir = os.path.join(dirs['abs_src_dir'],
                                self._query_objdir(),
                                'dist')
        cmd = ["find", find_dir, "-maxdepth", "1", "-type",
               "f", "-name", c['package_filename']]
        package_file_path = self.get_output_from_command(cmd,
                                                         dirs['abs_work_dir'])
        if not package_file_path:
            self.fatal("Can't determine filepath with cmd: %s" % (str(cmd),))

        cmd = ['openssl', 'dgst', '-' + c.get("hash_type", "sha512"),
               package_file_path]
        package_hash = self.get_output_from_command(cmd, dirs['abs_work_dir'])
        if not package_hash:
            self.fatal("undetermined package_hash with cmd: %s" % (str(cmd),))
        self.set_buildbot_property('packageFilename',
                                   os.path.split(package_file_path)[1],
                                   write_to_file=True)
        self.set_buildbot_property('packageSize',
                                   os.path.getsize(package_file_path),
                                   write_to_file=True)
        self.set_buildbot_property('packageHash',
                                   package_hash.strip().split(' ', 2)[1],
                                   write_to_file=True)

    def _do_sendchanges(self):
        c = self.config
        platform = self.buildbot_config['properties']['platform']
        talos_branch = "%s-%s-talos" % (self.branch, platform)
        installer_url = self.query_buildbot_property('packageUrl')
        tests_url = self.query_buildbot_property('testsUrl')
        sendchange_props = {
            'buildid': self.query_buildid(),
            'builduid': self.query_builduid(),
            'nightly_build': self.query_is_nightly(),
            'pgo_build': c['pgo_build'],
        }

        # TODO insert check for uploadMulti factory 2526
        # if not self.uploadMulti

        if c.get('enable_talos_sendchange'):
            self.sendchange(downloadables=[installer_url],
                            branch=talos_branch,
                            username='sendchange',
                            sendchange_props=sendchange_props)

        if c.get('enable_package_tests'):
            self.sendchange(downloadables=[installer_url, tests_url],
                            sendchange_props=sendchange_props)

    def _query_post_upload_cmd(self):
        # TODO support more from postUploadCmdPrefix()
        # as needed
        # h.m.o/build/buildbotcustom/process/factory.py#l119
        c = self.config
        post_upload_cmd = ["post_upload.py"]

        buildid = self.query_buildbot_property('buildid')
        revision = self.query_buildbot_property('got_revision')
        platform = c['stage_platform']
        if c['is_pgo']:
            platform += '-pgo'
        tinderboxBuildsDir = "%s-%s" % (self.branch, platform)

        post_upload_cmd.extend(["--tinderbox-builds-dir", tinderboxBuildsDir])
        post_upload_cmd.extend(["-p", c['stage_product']])
        post_upload_cmd.extend(['-i', buildid])
        post_upload_cmd.extend(['--revision', revision])
        post_upload_cmd.append('--release-to-tinderbox-dated-builds')

        return post_upload_cmd

    def read_buildbot_config(self):
        c = self.config
        if not c.get('is_automation'):
            return self._skip_buildbot_specific_action()
        super(BuildingMixin, self).read_buildbot_config()

    def setup_mock(self):
        """Override setup_mock found in MockMixin.

        Initializes and runs any mock initialization actions.
        Finally, installs packages.

        """
        if self.done_mock_setup:
            return

        c = self.config
        self.reset_mock(c['mock_target'])
        self.init_mock(c['mock_target'])
        if c.get('mock_pre_package_copy_files'):
            self.copy_mock_files(c['mock_target'],
                                 c.get('mock_pre_package_copy_files'))
        for cmd in c.get('mock_pre_package_cmds', []):
            self.run_mock_command(c['mock_target'], cmd, '/')
        if c.get('mock_packages'):
            self.install_mock_packages(c['mock_target'],
                                       c.get('mock_packages'))

        self.done_mock_setup = True

    def _checkout_source(self):
        """use vcs_checkout to grab source needed for build."""
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
            # TODO is rev not in buildbot_config (possibly multiple
            # times) as 'revision'?
            self.set_buildbot_property('got_revision',
                                       rev[:12],
                                       write_to_file=True)

    def preflight_build(self):
        """set up machine state for a complete build."""
        c = self.config
        dirs = self.query_abs_dirs()
        if c.get('enable_ccache'):
            self._ccache_z()
        if self.query_is_nightly():
            # TODO should we nuke the source dir during clobber?
            self.run_command(['rm', '-rf', dirs['abs_src_dir']],
                             cwd=dirs['abs_work_dir'],
                             env=self.query_env())
            # TODO do we still need this? check if builds are producing '20*'
            # files in basedir
            # self._rm_old_symbols()
        else:
            # the old package should live in source dir so we don't need to do
            # this for nighties
            self._rm_old_package()
        self._checkout_source()
        self._get_mozconfig()
        self._run_tooltool()

    def build(self):
        """build application."""
        # dependencies in config = ['ccache_env', 'old_packages']
        # see _pre_config_lock
        dirs = self.query_abs_dirs()
        base_cmd = 'make -f client.mk build'
        cmd = base_cmd + ' MOZ_BUILD_DATE=%s' % (self.query_buildid(),)
        if self.config['pgo_build']:
            cmd += ' MOZ_PGO=1'
        self._do_build_mock_make_cmd(cmd, dirs['abs_src_dir'])

    def generate_build_properties(self):
        """set buildid, sourcestamp, appVersion, and appName."""
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
            # TODO, do we need to set buildid twice like we already do in
            # self.query_buildid() ?
            {'ini_name': 'BuildID', 'prop_name': 'buildid'},
            {'ini_name': 'SourceStamp', 'prop_name': 'sourcestamp'},
            {'ini_name': 'Version', 'prop_name': 'appVersion'},
            {'ini_name': 'Name', 'prop_name': 'appName'}
        ]
        for prop in properties_needed:
            prop_val = self.get_output_from_command(
                base_cmd + [prop['ini_name']], cwd=dirs['base_work_dir']
            )
            self.set_buildbot_property(prop['prop_name'],
                                       prop_val,
                                       write_to_file=True)

    def generate_build_stats(self):
        """grab build stats following a compile.

        this action handles all statitics from a build:
        count_ctors, buildid, sourcestamp, and graph_server_post

        """
        # dependencies in config, see _pre_config_lock
        if self.config.get('enable_count_ctors'):
            self._count_ctors()
        else:
            self.info("count_ctors not enabled for this build. Skipping...")
        if self.config.get('graph_server'):
            self._graph_server_post()
        else:
            num_ctors = self.buildbot_properties.get('num_ctors', 'unknown')
            self.info("TinderboxPrint: num_ctors: %s" % (num_ctors,))

    def make_build_symbols(self):
        dirs = self.query_abs_dirs()
        cmd = 'make buildsymbols'
        cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        self._do_build_mock_make_cmd(cmd, cwd)

    def make_packages(self):
        c = self.config
        dirs = self.query_abs_dirs()
        # dependencies in config, see _pre_config_lock

        # make package-tests
        if c.get('enable_package_tests'):
            cmd = 'make package-tests'
            cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
            self._do_build_mock_make_cmd(cmd, cwd)

        # make package
        cmd = 'make package'
        cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        self._do_build_mock_make_cmd(cmd, cwd)

        # TODO check for if 'rpm' not in self.platform_variation and
        # self.productName not in ('xulrunner', 'b2g'):
        self._set_package_file_properties()

    def make_upload(self):
        c = self.config
        dirs = self.query_abs_dirs()
        # dependencies in config = ['upload_env', 'stage_platform',
        # 'mock_target']
        # see _pre_config_lock

        cwd = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        # we want the env without MOZ_SIGN_CMD
        upload_env = self.query_env()
        upload_env.update(c['upload_env'])
        # _query_post_upload_cmd returns a list (a cmd list), for env sake here
        # let's make it a string
        pst_up_cmd = ' '.join([str(i) for i in self._query_post_upload_cmd()])
        upload_env['POST_UPLOAD_CMD'] = pst_up_cmd
        parser = MakeUploadOutputParser(config=c,
                                        log_obj=self.log_obj)
        self._do_build_mock_make_cmd('make upload',
                                     cwd=cwd,
                                     env=upload_env,
                                     output_parser=parser)
        self.info('Setting properties from make upload...')
        for prop, value in parser.matches.iteritems():
            self.set_buildbot_property(prop,
                                       value,
                                       write_to_file=True)
        self._do_sendchanges()

    def test_pretty_names(self):
        # dependencies in config
        # see _pre_config_lock
        c = self.config
        dirs = self.query_abs_dirs()
        env = self.query_env()
        objdir_path = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        base_cmd = 'make %s MOZ_PKG_PRETTYNAMES=1'

        self._do_build_mock_make_cmd(base_cmd % ("package",),
                                     cwd=objdir_path,
                                     env=env)
        update_package_cmd = '-C %s' % (os.path.join(objdir_path, 'tools',
                                                     'update-packaging'),)
        self._do_build_mock_make_cmd(base_cmd % (update_package_cmd,),
                                     cwd=dirs['abs_src_dir'],
                                     env=env)
        if c['l10n_check_test']:
            self._do_build_mock_make_cmd(base_cmd % ("l10n-check",),
                                         cwd=objdir_path,
                                         env=env)
            # make l10n-hcek again without pretty names?
            self._do_build_mock_make_cmd('make l10n-check',
                                         cwd=objdir_path,
                                         env=env)

    def check_test_complete(self):
        c = self.config
        dirs = self.query_abs_dirs()
        objdir_path = os.path.join(dirs['abs_src_dir'], self._query_objdir())
        abs_check_test_env = {}
        for env_var, env_value in c['check_test_env'].iteritems():
            abs_check_test_env[env_var] = os.path.join(dirs['abs_tools_dir'],
                                                       env_value)
        env = self.query_env()
        env.update(abs_check_test_env)
        parser = CheckTestCompleteParser(config=c,
                                         log_obj=self.log_obj)
        self._do_build_mock_make_cmd('make -k check',
                                     cwd=objdir_path,
                                     env=env,
                                     output_parser=parser)
        parser.evaluate_parser()

    def enable_ccache(self):
        dirs = self.query_abs_dirs()
        env = self.query_env()
        cmd = ['ccache', '-s']
        self.run_command(cmd, cwd=dirs['abs_src_dir'], env=env)
