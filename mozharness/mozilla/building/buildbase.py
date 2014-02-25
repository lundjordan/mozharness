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
import copy
import glob
from itertools import chain

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
from mozharness.base.log import FATAL

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

SNIPPET_TEMPLATE = """version=2
type=%(type)s
url=%(url)s
hashFunction=sha512
hashValue=%(sha512_hash)s
size=%(size)d
build=%(buildid)s
displayVersion=%(version)s
appVersion=%(version)s
platformVersion=%(version)s
"""

MISSING_CFG_KEY_MSG = "The key '%s' could not be determined \
Please add this to your config."

ERROR_MSGS = {
    'undetermined_repo_path': 'The repo_path could not be determined. \
Please make sure there is a "repo_path" in either your config or, if \
you are running this in buildbot, in your buildbot_config.',
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
    # let's create a switch case using name-spaces/dict
    # rather than a long if/else with duplicate code
    property_conditions = {
        # key: property name, value: condition
        # TODO I think we can rm these RPM conditions
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

    def __init__(self, **kwargs):
        self.matches = {}
        super(MakeUploadOutputParser, self).__init__(**kwargs)

    def parse_single_line(self, line):
        pat = r'''^(https?://.*?\.(?:tar\.bz2|dmg|zip|apk|rpm|mar|tar\.gz))$'''
        m = re.compile(pat).match(line)
        if m:
            m = m.group(1)
            for prop, condition in self.property_conditions.iteritems():
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
            if dep not in c:
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
        if self.buildbot_config['properties'].get('builduid'):
            self.builduid = self.buildbot_config['properties']['builduid']
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
            self.buildid = self.buildbot_config['properties']['buildid']
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
            return self.fatal(MISSING_CFG_KEY_MSG % ('objdir',))
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

    def query_build_env(self, skip_keys=None, replace_dict=None, **kwargs):
        c = self.config
        env = {}
        if skip_keys is None:
            skip_keys = []

        if not replace_dict:
            replace_dict = {}
        # now let's grab the right host based off staging/production
        # symbol_server_host is defined in build_pool_specifics.py
        replace_dict.update({"symbol_server_host": c['symbol_server_host']})

        # let's envoke the base query_env and make a copy of it
        # as we don't always want every key below added to the same dict
        env = copy.deepcopy(
            super(BuildingMixin, self).query_env(replace_dict=replace_dict,
                                                 **kwargs)
        )

        if self.query_is_nightly():
            env["IS_NIGHTLY"] = "yes"
            if c["create_snippets"] and c['platform_supports_snippets']:
                # in branch_specifics.py we might set update_channel explicitly
                if c.get('update_channel'):
                    env["MOZ_UPDATE_CHANNEL"] = c['update_channel']
                else:  # let's just give the generic channel based on branch
                    env["MOZ_UPDATE_CHANNEL"] = "nightly-%s" % (self.branch,)

        if c.get('enable_signing') and 'MOZ_SIGN_CMD' not in skip_keys:
            moz_sign_cmd = self.query_moz_sign_cmd()
            env["MOZ_SIGN_CMD"] = subprocess.list2cmdline(moz_sign_cmd)

        # we can't make env an attribute of self because env can change on
        # every call to this method for reasons like MOZ_SIGN_CMD
        return env

    def _ccache_z(self):
        """clear ccache stats."""
        self._assert_cfg_valid_for_action(['ccache_env'], 'build')
        c = self.config
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        # update env for just this command
        ccache_env = copy.deepcopy(c['ccache_env'])
        ccache_env['CCACHE_BASEDIR'] = c['ccache_env'].get(
            'CCACHE_BASEDIR', "") % {"base_dir": dirs['base_work_dir']}
        env.update(c['ccache_env'])
        if os.path.exists(dirs['abs_src_dir']):
            self.run_command(command=['ccache', '-z'],
                             cwd=dirs['abs_src_dir'],
                             env=env)

    def _rm_old_package(self):
        """rm the old package."""
        c = self.config
        dirs = self.query_abs_dirs()
        cmd = ["rm", "-rf"]
        old_packages = c.get('old_packages')

        for product in old_packages:
            cmd.append(product % {"objdir": dirs['abs_obj_dir']})
        self.info("removing old packages...")
        if dirs['abs_src_dir']:
            self.run_command(cmd, cwd=dirs['abs_src_dir'])

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

    # TODO add this or merge to ToolToolMixin
    def _run_tooltool(self):
        self._assert_cfg_valid_for_action(
            ['tooltool_script', 'tooltool_bootstrap', 'tooltool_url_list'],
            'build'
        )
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
            self.set_buildbot_property('got_revision',
                                       rev[:12],
                                       write_to_file=True)

    def _count_ctors(self):
        """count num of ctors and set testresults."""
        dirs = self.query_abs_dirs()
        testresults = []
        abs_count_ctors_path = os.path.join(dirs['abs_tools_dir'],
                                            'buildfarm',
                                            'utils',
                                            'count_ctors.py')
        abs_libxul_path = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'bin',
                                       'libxul.so')

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

    def _create_complete_mar(self):
        # TODO use mar.py MIXINs
        self._assert_cfg_valid_for_action(
            ['mock_target', 'complete_mar_pattern'],
            'make-update'
        )
        self.info('Creating a complete mar:')
        c = self.config
        env = self.query_build_env()
        dirs = self.query_abs_dirs()
        dist_update_dir = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'update')
        self.info('removing existing mar...')
        mar_file_results = glob.glob(os.path.join(dist_update_dir, '*.mar'))
        if mar_file_results:
            for mar_file in mar_file_results:
                self.rmtree(mar_file, error_level=FATAL)
        else:
            self.info('no existing mar found with pattern: %s' % (
                os.path.join(dist_update_dir, '*.mar'),))
        self.info('making a complete new mar...')
        update_pkging_path = os.path.join(dirs['abs_obj_dir'],
                                          'tools',
                                          'update-packaging')
        self.run_mock_command(c['mock_target'],
                              command='make -C %s' % (update_pkging_path,),
                              cwd=dirs['abs_src_dir'],
                              env=env)
        self._set_file_properties(file_name=c['complete_mar_pattern'],
                                  find_dir=dist_update_dir,
                                  prop_type='completeMar')

    def _create_partial_mar(self):
        # TODO use mar.py MIXINs
        self._assert_cfg_valid_for_action(
            ['mock_target', 'update_env', 'platform_ftp_name', 'stage_server'],
            'upload'
        )
        self.info('Creating a partial mar:')
        c = self.config
        dirs = self.query_abs_dirs()
        generic_env = self.query_build_env()
        update_env = dict(chain(generic_env.items(), c['update_env'].items()))
        abs_unwrap_update_path = os.path.join(dirs['abs_src_dir'],
                                              'tools',
                                              'update-packaging',
                                              'unwrap_full_update.pl')
        dist_update_dir = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'update')
        self.info('removing old unpacked dirs...')
        for f in ['current', 'current.work', 'previous']:
            self.rmtree(os.path.join(dirs['abs_obj_dir'], f),
                        error_level=FATAL)
        self.info('making unpacked dirs...')
        for f in ['current', 'previous']:
            self.mkdir_p(os.path.join(dirs['abs_obj_dir'], f),
                         error_level=FATAL)
        self.info('unpacking current mar...')
        mar_file = self.query_buildbot_property('completeMarFilename')
        cmd = '%s %s %s' % (self.query_exe('perl'),
                            abs_unwrap_update_path,
                            os.path.join(dist_update_dir, mar_file))
        self.run_mock_command(c['mock_target'],
                              command=cmd,
                              cwd=os.path.join(dirs['abs_obj_dir'], 'current'),
                              env=update_env,
                              halt_on_failure=True)
        # The mar file name will be the same from one day to the next,
        # *except* when we do a version bump for a release. To cope with
        # this, we get the name of the previous complete mar directly
        # from staging. Version bumps can also often involve multiple mars
        # living in the latest dir, so we grab the latest one.
        self.info('getting previous mar filename...')
        latest_mar_dir = c['latest_mar_dir'] % {'branch': self.branch}
        cmd = 'ssh -l %s -i ~/.ssh/%s %s ls -1t %s | grep %s$ | head -n 1' % (
            c['stage_username'], c['stage_ssh_key'], c['stage_server'],
            latest_mar_dir, c['platform_ftp_name']
        )
        previous_mar_file = self.get_output_from_command(cmd)
        if not re.search(r'\.mar$', previous_mar_file):
            self.fatal('could not determine the previous complete mar file')
        previous_mar_url = "http://%s%s/%s" % (c['stage_server'],
                                               latest_mar_dir,
                                               previous_mar_file)
        self.info('downloading previous mar...')
        # use self.download_file(self, url, file_name=None
        self.download_file(previous_mar_url,
                           file_name='previous.mar',
                           parent_dir=dist_update_dir,
                           error_level=FATAL)
        self.info('unpacking previous mar...')
        cmd = '%s %s %s' % (self.query_exe('perl'),
                            abs_unwrap_update_path,
                            os.path.join(dist_update_dir, 'previous.mar'))
        self.run_mock_command(c['mock_target'],
                              command=cmd,
                              cwd=os.path.join(dirs['abs_obj_dir'],
                                               'previous'),
                              env=update_env,
                              halt_on_failure=True)
        # Extract the build ID from the unpacked previous complete mar.
        previous_buildid = self._query_previous_buildid()
        self.info('removing pgc files from previous and current dirs')
        for mar_dir in ['current', 'previous']:
            target_path = os.path.join(dirs['abs_obj_dir'], mar_dir)
            if os.path.exists(target_path):
                for root, dirs, file_names in os.walk(target_path):
                    for file_name in file_names:
                        if file_name.endswith('.pgc'):
                            self.info('removing file: %s' % (file_name,))
                            os.remove(file_name)
        self.info("removing existing partial mar...")
        mar_file_results = glob.glob(
            os.path.join(dist_update_dir, '*.partial.*.mar')
        )
        if not mar_file_results:
            self.warning("Could not determine existing partial mar from "
                         "%s pattern in %s dir" % ('*.partial.*.mar',
                                                   dist_update_dir))
        for mar_file in mar_file_results:
            self.rmtree(mar_file, error_level=FATAL)

        self.info('generating partial patch from two complete mars...')
        make_partial_env = {
            'STAGE_DIR': '../../dist/update',
            'SRC_BUILD': '../../previous',
            'SRC_BUILD_ID': previous_buildid,
            'DST_BUILD': '../../current',
            'DST_BUILD_ID': self.query_buildid()
        }
        cmd = 'make -C tools/update-packaging partial-patch',
        self.run_mock_command(c.get('mock_target'),
                              command=cmd,
                              cwd=self.query_abs_dirs()['abs_obj_dir'],
                              env=dict(chain(update_env.items(),
                                             make_partial_env.items())),
                              halt_on_failure=True)
        self.rmtree(os.path.join(dist_update_dir, 'previous.mar'),
                    error_level=FATAL)
        self._set_file_properties(file_name=c['partial_mar_pattern'],
                                  find_dir=dist_update_dir,
                                  prop_type='partialMar')

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
        self._assert_cfg_valid_for_action(
            ['base_name', 'graph_server', 'graph_selector'],
            'generate-build-stats'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        graph_server_post_path = os.path.join(dirs['abs_tools_dir'],
                                              'buildfarm',
                                              'utils',
                                              'graph_server_post.py')
        gs_pythonpath = os.path.join(dirs['abs_tools_dir'],
                                     'lib',
                                     'python')
        # graph server takes all our build properties we had initially
        # (buildbot_config) and what we updated to since
        # the script ran (buildbot_properties)
        # TODO it would be better to grab all the properties that were
        # persisted to file rather than use whats in the buildbot_properties
        # live object so we become less action dependant.
        graph_props_path = os.path.join(c['base_work_dir'],
                                        "properties",
                                        "graph_props.json")
        all_current_props = dict(
            chain(self.buildbot_config['properties'].items(),
                  self.buildbot_properties.items())
        )
        self.dump_buildbot_properties_to_json(all_current_props,
                                              graph_props_path)

        gs_env = self.query_build_env()
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
        cmd.extend(['--properties-file', graph_props_path])
        cmd.extend(['--timestamp', str(self.epoch_timestamp)])

        self.info("Obtaining graph server post results")
        result_code = self.retry(self.run_command,
                                 args=(cmd,),
                                 kwargs={'cwd': dirs['abs_src_dir'],
                                         'env': gs_env})
        # TODO find out if this translates to the same from this file:
        # http://mxr.mozilla.org/build/source/buildbotcustom/steps/test.py#73
        if result_code != 0:
            self.error('Automation Error: failed graph server post')
        else:
            self.info("graph server post ok")

    def _set_file_properties(self, file_name, find_dir, prop_type):
        c = self.config
        dirs = self.query_abs_dirs()
        cmd = ["find", find_dir, "-maxdepth", "1", "-type",
               "f", "-name", file_name]
        file_path = self.get_output_from_command(cmd,
                                                 dirs['abs_work_dir'])
        if not file_path:
            self.fatal("Can't determine filepath with cmd: %s" % (str(cmd),))

        cmd = ['openssl', 'dgst', '-' + c.get("hash_type", "sha512"),
               file_path]
        hash_prop = self.get_output_from_command(cmd, dirs['abs_work_dir'])
        if not hash_prop:
            self.fatal("undetermined hash_prop with cmd: %s" % (str(cmd),))
        self.set_buildbot_property(prop_type + 'Filename',
                                   os.path.split(file_path)[1],
                                   write_to_file=True)
        self.set_buildbot_property(prop_type + 'Size',
                                   os.path.getsize(file_path),
                                   write_to_file=True)
        self.set_buildbot_property(prop_type + 'Hash',
                                   hash_prop.strip().split(' ', 2)[1],
                                   write_to_file=True)

    def _query_previous_buildid(self):
        dirs = self.query_abs_dirs()
        previous_buildid = self.query_buildbot_property('previous_buildid')
        if previous_buildid:
            return previous_buildid
        cmd = [
            "find", "previous", "-maxdepth", "4", "-type", "f", "-name",
            "application.ini"
        ]
        self.info("finding previous mar's inipath...")
        prev_ini_path = self.get_output_from_command(cmd,
                                                     cwd=dirs['abs_obj_dir'],
                                                     halt_on_failure=True)
        print_conf_path = os.path.join(dirs['abs_src_dir'],
                                       'config',
                                       'printconfigsetting.py')
        abs_prev_ini_path = os.path.join(dirs['abs_obj_dir'], prev_ini_path)
        previous_buildid = self.get_output_from_command(['python',
                                                         print_conf_path,
                                                         abs_prev_ini_path,
                                                         'App', 'BuildID'])
        if not previous_buildid:
            self.fatal("Could not determine previous_buildid. This property"
                       "requires the upload action creating a partial mar.")
        self.set_buildbot_property("previous_buildid",
                                   previous_buildid,
                                   write_to_file=True)
        return previous_buildid

    def _query_post_upload_cmd(self):
        # TODO support more from postUploadCmdPrefix()
        # as needed (as we introduce builds that use it)
        # h.m.o/build/buildbotcustom/process/factory.py#l119
        self._assert_cfg_valid_for_action(['stage_product'], 'upload')
        c = self.config
        post_upload_cmd = ["post_upload.py"]
        buildid = self.query_buildbot_property('buildid')
        revision = self.query_buildbot_property('got_revision')
        platform = self.platform
        if c.get('pgo_build'):
            platform += '-pgo'
        tinderboxBuildsDir = "%s-%s" % (self.branch, platform)

        post_upload_cmd.extend(["--tinderbox-builds-dir", tinderboxBuildsDir])
        post_upload_cmd.extend(["-p", c['stage_product']])
        post_upload_cmd.extend(['-i', buildid])
        post_upload_cmd.extend(['--revision', revision])
        post_upload_cmd.append('--release-to-tinderbox-dated-builds')
        if self.query_is_nightly():
            post_upload_cmd.extend(['-b', self.branch])
            post_upload_cmd.append('--release-to-dated')
            if c['platform_supports_post_upload_to_latest']:
                post_upload_cmd.append('--release-to-latest')
        return post_upload_cmd

    def _grab_mar_props(self, snippet_type='complete'):
        return (self.query_buildbot_property('%sMarUrl' % (snippet_type)),
                self.query_buildbot_property('%sMarHash' % (snippet_type)),
                self.query_buildbot_property('%sMarSize' % (snippet_type)))

    def _get_snippet_values(self, snippet_dir, snippet_type='complete'):
        fatal_msg = ("Can't determine the '%s' prop and it's needed for "
                     "creating snippets. Please run the action 'upload' prior"
                     "to this")
        c = self.config
        buildid = self.query_buildid()
        url, hash_val, size = self._grab_mar_props(snippet_type)
        if not url or not hash_val or not size:
            self._assert_cfg_valid_for_action(
                ['%s_mar_pattern' % (snippet_type,)], 'update'
            )
            self._set_file_properties(
                file_name=c['%s_mar_pattern' % (snippet_type,)],
                find_dir=snippet_dir, prop_type='completeMar'
            )
            # now try, try again!
            url, hash_val, size = self._grab_mar_props(snippet_type)
        version = self.query_buildbot_property('appVersion')
        if not version:
            self._set_build_props()
            # now try, try again!
            version = self.query_buildbot_property('appVersion')

        if not url:
            self.fatal(fatal_msg % ('%sMarUrl' % (snippet_type,),))
        if not hash_val:
            self.fatal(fatal_msg % ('%sMarHash' % (snippet_type,),))
        if not size:
            self.fatal(fatal_msg % ('%sMarSize' % (snippet_type,),))
        if not version:
            self.fatal(fatal_msg % ('appVersion',))
        return {
            'type': snippet_type,
            'url': url,
            'sha512_hash': hash_val,
            'size': size,
            'buildid': buildid,
            'version': version,
        }

    def _create_snippet(self, snippet_type):
        # TODO port to mozharness/mozilla/signing.py.
        # right now, the existing create_snippet method is conducted
        # differently. these should be merged
        self._assert_cfg_valid_for_action(
            ['mock_target'], 'update'
        )
        dirs = self.query_abs_dirs()
        snippet_dir = os.path.join(dirs['abs_obj_dir'],
                                   'dist',
                                   'update')
        if not os.path.exists(snippet_dir):
            self.fatal("The path: '%s' needs to exist for this action"
                       "Have you ran the 'build' action?" % (snippet_dir,))
        abs_snippet_path = os.path.join(snippet_dir,
                                        '%s.update.snippet' % (snippet_type,))
        content = SNIPPET_TEMPLATE % self._get_snippet_values(snippet_dir,
                                                              snippet_type)
        self.info('saving snippet to file...')
        if self.write_to_file(abs_snippet_path, content) is None:
            self.error("Unable to write %s snippet to %s!" % (
                snippet_type, abs_snippet_path)
            )
        self.info("displaying %s snippet file contents..." % (snippet_type,))
        with open(abs_snippet_path) as f:
            for line in f:
                self.info(line)

    def _submit_balrog_updates(self):
        c = self.config
        dirs = self.query_abs_dirs()
        # first download buildprops_balrog.json this should be all the
        # buildbot properties we got initially (buildbot_config) and what
        # we have updated with since the script ran (buildbot_properties)
        # TODO it would be better to grab all the properties that were
        # persisted to file rather than use whats in the
        # buildbot_properties live object. However, this should work for
        # now and balrog may be removing the buildprops cli arg once we no
        # longer use buildbot
        balrog_props_path = os.path.join(c['base_work_dir'],
                                         "properties",
                                         "balrog_props.json")
        balrog_submitter_path = os.path.join(dirs['abs_tools_dir'],
                                             'scripts',
                                             'updates',
                                             'balrog-submitter.py')
        all_current_props = dict(
            chain(self.buildbot_config['properties'].items(),
                  self.buildbot_properties.items())
        )
        self.dump_buildbot_properties_to_json(all_current_props,
                                              balrog_props_path)
        cmd = [
            self.query_exe('python'),
            balrog_submitter_path,
            '--build-properties', balrog_props_path,
            '--api-root', c['balrog_api_root'],
            '--verbose',
        ]
        if c['balrog_credentials_file']:
            self.info("Using Balrog credential file...")
            abs_balrog_cred_file = os.path.join(
                c['base_work_dir'], c['balrog_credentials_file']
            )
            if not abs_balrog_cred_file:
                self.fatal("credential file given but doesn't exist!"
                           " Path given: %s" % (abs_balrog_cred_file))
            cmd.extend(['--credentials-file', abs_balrog_cred_file])
        self.info("Submitting Balrog updates...")
        self.info("debug, normally would run: %s" % (str(cmd)))
        # XXX
        # self.retry(self.run_command, args=(cmd,))

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
        self._assert_cfg_valid_for_action(['mock_target'], 'setup-mock')
        c = self.config
        self.init_mock(c['mock_target'])
        if c.get('mock_pre_package_copy_files'):
            self.copy_mock_files(c['mock_target'],
                                 c.get('mock_pre_package_copy_files'))
        for cmd in c.get('mock_pre_package_cmds', []):
            self.run_mock_command(c['mock_target'], cmd, '/')
        if c.get('mock_packages'):
            self.install_mock_packages(c['mock_target'],
                                       list(c.get('mock_packages')))
        self.done_mock_setup = True

    def preflight_build(self):
        """set up machine state for a complete build."""
        c = self.config
        if c.get('enable_ccache'):
            self._ccache_z()
        if not self.query_is_nightly():
            # the old package should live in source dir so we don't need to do
            # this for nighties since we clobber the whole work_dir in
            # clobber()
            self._rm_old_package()
        self._checkout_source()
        self._get_mozconfig()
        self._run_tooltool()

    def build(self):
        """build application."""
        # dependencies in config see _pre_config_lock
        base_cmd = 'make -f client.mk build'
        cmd = base_cmd + ' MOZ_BUILD_DATE=%s' % (self.query_buildid(),)
        if self.config.get('pgo_build'):
            cmd += ' MOZ_PGO=1'
        self.run_mock_command(self.config.get('mock_target'),
                              command=cmd,
                              cwd=self.query_abs_dirs()['abs_src_dir'],
                              env=self.query_build_env())

    def generate_build_props(self):
        """set buildid, sourcestamp, appVersion, and appName."""
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config',
                                               'printconfigsetting.py')
        application_ini_path = os.path.join(dirs['abs_obj_dir'],
                                            'dist',
                                            'bin',
                                            'application.ini')
        if (not os.path.exists(print_conf_setting_path) or
                not os.path.exists(application_ini_path)):
            self.fatal("Can't set the following properties: "
                       "buildid, sourcestamp, appVersion, and appName. "
                       "Required paths missing. Verify both %s and %s "
                       "exist. These paths require the 'build' action to be "
                       "run prior to this" % (print_conf_setting_path,
                                              application_ini_path))
        base_cmd = [
            'python', print_conf_setting_path, application_ini_path, 'App'
        ]
        properties_needed = [
            # TODO, do we need to set buildid since we already do in
            # self.query_buildid() ?
            # {'ini_name': 'BuildID', 'prop_name': 'buildid'},
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
        count_ctors and graph_server_post

        """
        self._count_ctors()
        # TODO in buildbot, we see if self.graphServer exists, but we know that
        # nightly does not use graph server so let's use that instead of adding
        # confusion to the configs. This may need to change once we
        # port xul, valgrind, etc over and it turns out we need the
        # graph_server condition
        # if self.config.get('graph_server'):
        if not self.query_is_nightly():
            self._graph_server_post()
        else:
            num_ctors = self.buildbot_properties.get('num_ctors', 'unknown')
            self.info("TinderboxPrint: num_ctors: %s" % (num_ctors,))

    def symbols(self):
        c = self.config
        cwd = self.query_abs_dirs()['abs_obj_dir']
        env = self.query_build_env()
        self.run_mock_command(c.get('mock_target'),
                              command='make buildsymbols',
                              cwd=cwd,
                              env=env)
        # TODO this condition might be extended with xul, valgrind, etc as more
        # variants are added
        # not all nightly platforms upload symbols!
        if self.query_is_nightly() and c.get('upload_symbols'):
            self.retry(
                self.run_mock_command,
                kwargs={'mock_target': c.get('mock_target'),
                        'command': 'make uploadsymbols',
                        'cwd': cwd,
                        'env': env}
            )

    def packages(self):
        self._assert_cfg_valid_for_action(['mock_target', 'package_filename'],
                                          'make-packages')
        c = self.config
        cwd = self.query_abs_dirs()['abs_obj_dir']

        # make package-tests
        if c.get('enable_package_tests'):
            self.run_mock_command(c['mock_target'],
                                  command='make package-tests',
                                  cwd=cwd,
                                  env=self.query_build_env())

        # make package
        self.run_mock_command(c['mock_target'],
                              command='make package',
                              cwd=cwd,
                              env=self.query_build_env())

        # TODO check not 'xulrunner' (when we do xulrunner builds)
        # I don't think we actually need package_filename, size, hash, etc. but
        # it may turn out that we will. commenting out for now
        # find_dir = os.path.join(self.query_abs_dirs()['abs_obj_dir'],
        #                         'dist')
        # NOTE package_filename can be obtained by build sys: eg `make
        # echo-variable-PACKAGE` However, this env var is not always correct
        # and may be influenced by things like: MOZ_OFFICIAL=1,
        # MOZ_PKG_PRETTYNAMES=1 and on windows, there is more than one package
        # name. for now, let's use the package_filename pattern to search for
        # it manually with 'find' cmd
        # self._set_file_properties(file_name=c['package_filename'],
        #                           find_dir=find_dir,
        #                           prop_type='package')

    def upload(self):
        self._assert_cfg_valid_for_action(
            ['mock_target', 'upload_env', 'create_snippets',
             'platform_supports_snippets', 'create_partial',
             'platform_supports_partials', 'stage_server'], 'upload'
        )
        c = self.config
        if self.query_is_nightly():
            # if branch supports snippets and platform supports snippets
            if c['create_snippets'] and c['platform_supports_snippets']:
                self._create_complete_mar()
                if c['create_partial'] and c['platform_supports_partials']:
                    self._create_partial_mar()

        upload_env = self.query_build_env()
        upload_env.update(c['upload_env'])
        upload_env['UPLOAD_HOST'] = upload_env['UPLOAD_HOST'] % {
            "stage_server": c['stage_server']}

        # _query_post_upload_cmd returns a list (a cmd list), for env sake here
        # let's make it a string
        pst_up_cmd = ' '.join([str(i) for i in self._query_post_upload_cmd()])
        upload_env['POST_UPLOAD_CMD'] = pst_up_cmd
        parser = MakeUploadOutputParser(config=c,
                                        log_obj=self.log_obj)
        cwd = self.query_abs_dirs()['abs_obj_dir']
        self.retry(
            self.run_mock_command, kwargs={'mock_target': c.get('mock_target'),
                                           'command': 'make upload',
                                           'cwd': cwd,
                                           'env': upload_env,
                                           'output_parser': parser}
        )
        self.info('Setting properties from make upload...')
        for prop, value in parser.matches.iteritems():
            self.set_buildbot_property(prop,
                                       value,
                                       write_to_file=True)

    def sendchanges(self):
        c = self.config

        installer_url = self.query_buildbot_property('packageUrl')
        tests_url = self.query_buildbot_property('testsUrl')
        sendchange_props = {
            'buildid': self.query_buildid(),
            'builduid': self.query_builduid(),
            'nightly_build': self.query_is_nightly(),
            'pgo_build': c.get('pgo_build', False),
        }
        # TODO insert check for uploadMulti factory 2526
        # if not self.uploadMulti when we introduce a platform/build that uses
        # uploadMulti

        if c.get('enable_talos_sendchange'):  # do talos sendchange
            if c.get('pgo_build'):
                build_type = 'pgo-'
            else:  # we don't do talos sendchange for debug so no need to check
                build_type = ''  # leave 'opt' out of branch for talos
            talos_branch = "%s-%s-%s%s" % (self.branch,
                                           self.platform,
                                           build_type,
                                           'talos')
            self.sendchange(downloadables=[installer_url],
                            branch=talos_branch,
                            username='sendchange',
                            sendchange_props=sendchange_props)
        if c.get('enable_package_tests'):  # do unittest sendchange
            if c.get('pgo_build'):
                build_type = 'pgo'
            if c.get('debug_build'):
                build_type = 'debug'
            else:  # generic opt build
                build_type = 'opt'
            unittest_branch = "%s-%s-%s-%s" % (self.branch,
                                               self.platform,
                                               build_type,
                                               'unittest')
            self.sendchange(downloadables=[installer_url, tests_url],
                            branch=unittest_branch,
                            sendchange_props=sendchange_props)

    def pretty_names(self):
        self._assert_cfg_valid_for_action(
            ['mock_target'], 'prett-names'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        # we want the env without MOZ_SIGN_CMD
        env = self.query_build_env(skip_keys=['MOZ_SIGN_CMD'])
        base_cmd = 'make %s MOZ_PKG_PRETTYNAMES=1'

        # TODO  port below from process/factory.py line 1526 if we end up
        # porting mac before x-compiling
        # MAC OS X IMPLEMENTATION
        # if 'mac' in self.platform:
        #     self.addStep(ShellCommand(
        #                  name='postflight_all',
        #                  command=self.makeCmd + [
        #                  '-f', 'client.mk', 'postflight_all'],

        package_targets = ['package']
        # TODO  port below from process/factory.py line 1543
        # WINDOWS IMPLEMENTATION
        # if self.enableInstaller:
        #     pkg_targets.append('installer')
        for target in package_targets:
            self.run_mock_command(c['mock_target'],
                                  command=base_cmd % (target,),
                                  cwd=dirs['abs_obj_dir'],
                                  env=env)
        update_package_cmd = '-C %s' % (os.path.join(dirs['abs_obj_dir'],
                                                     'tools',
                                                     'update-packaging'),
                                        )
        self.run_mock_command(c['mock_target'],
                              command=base_cmd % (update_package_cmd,),
                              cwd=dirs['abs_src_dir'],
                              env=env)
        if c.get('do_pretty_name_l10n_check'):
            self.run_mock_command(c['mock_target'],
                                  command=base_cmd % ("l10n-check",),
                                  cwd=dirs['abs_obj_dir'],
                                  env=env)

    def check_l10n(self):
        self._assert_cfg_valid_for_action(
            ['mock_target'], 'check-l10n'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        # we want the env without MOZ_SIGN_CMD
        env = self.query_build_env(skip_keys=['MOZ_SIGN_CMD'])
        self.run_mock_command(c['mock_target'],
                              command='make l10n-check',
                              cwd=dirs['abs_obj_dir'],
                              env=env)

    def check_test(self):
        self._assert_cfg_valid_for_action(
            ['mock_target', 'check_test_env'], 'check-test'
        )
        if self.query_is_nightly():
            self.info("Skipping action because this is a nightly run...")
            return
        self._assert_cfg_valid_for_action(['check_test_env'],
                                          'check-test-complete')
        c = self.config
        dirs = self.query_abs_dirs()
        abs_check_test_env = {}
        for env_var, env_value in c['check_test_env'].iteritems():
            abs_check_test_env[env_var] = os.path.join(dirs['abs_tools_dir'],
                                                       env_value)
        env = self.query_build_env()
        env.update(abs_check_test_env)
        parser = CheckTestCompleteParser(config=c,
                                         log_obj=self.log_obj)
        self.run_mock_command(c['mock_target'],
                              command='make -k check',
                              cwd=dirs['abs_obj_dir'],
                              env=env,
                              output_parser=parser)
        parser.evaluate_parser()

    def update(self):
        self._assert_cfg_valid_for_action(
            ['create_snippets', 'platform_supports_snippets',
             'create_partial', 'platform_supports_partials',
             'aus2_user', 'aus2_ssh_key', 'aus2_host',
             'aus2_base_upload_dir', 'update_platform', 'balrog_api_root'],
            'update'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        # XXX FOR DEBUGGING
        for val in ['create_snippets', 'platform_supports_snippets',
                    'create_partial', 'platform_supports_partials',
                    'aus2_user', 'aus2_ssh_key', 'aus2_host',
                    'aus2_base_upload_dir', 'update_platform',
                    'balrog_api_root']:

            self.info(val + ": " + str(c[val]))
        if not self.query_is_nightly() and (
                c['create_snippets'] and c['platform_supports_snippets']):
            self.info("Skipping action because this action is only done for "
                      "nightlies and that support/enable snippets...")
            return
        dist_update_dir = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'update')
        base_ssh_cmd = 'ssh -l %s -i ~/.ssh/%s %s ' % (c['aus2_user'],
                                                       c['aus2_ssh_key'],
                                                       c['aus2_host'])
        root_aus_full_dir = "%s/%s/%s" % (c['aus2_base_upload_dir'],
                                          self.branch,
                                          c['update_platform'])
        ##### Create snippet steps
        # create a complete snippet
        self._create_snippet('complete')
        buildid = self.query_buildid()
        # if branch supports partials and platform supports partials
        if c['create_partial'] and c['platform_supports_partials']:
            # now create a partial snippet
            self._create_snippet('partial')
            # let's change the buildid to be the previous buildid
            # because that the previous upload dir uses that id
            buildid = self._query_previous_buildid()
        #####

        ##### Upload snippet steps
        self.info("Creating AUS previous upload dir")
        aus_prev_upload_dir = "%s/%s/en-US" % (root_aus_full_dir,
                                               buildid)
        cmd = 'mkdir -p %s' % (aus_prev_upload_dir,)
        self.info("debug, normally would run: %s" % (str(base_ssh_cmd + cmd)))
        # XXX
        # self.retry(self.run_command, args=(base_ssh_cmd + cmd,))

        # make an upload command that supports complete and partial formatting
        upload_cmd = ('scp -o User=%s -o IdentityFile=~/.ssh/%s'
                      ' %s/%%s.update.snippet %s:%s/%%s.txt' % (
                          c['aus2_user'], c['aus2_ssh_key'], dist_update_dir,
                          c['aus2_host'], aus_prev_upload_dir)
                      )
        self.info("uploading complete snippet")
        self.info("debug, normally would run: %s" % (
            str(upload_cmd % ('complete', 'complete'),)))
        # XXX
        # self.retry(self.run_command,
        #            args=(upload_cmd % ('complete', 'complete'),))
        # if branch supports partials and platform supports partials
        if c['create_partial'] and c['platform_supports_partials']:
            self.info("uploading partial snippet")
            self.info("debug, normally would run: %s" % (
                str(upload_cmd % ('partial', 'partial'),)))
            # XXX
            # self.retry(self.run_command,
            #            args=(upload_cmd % ('partial', 'partial'),))
            self.info("creating aus current upload dir")
            aus_current_upload_dir = "%s/%s/en-US" % (root_aus_full_dir,
                                                      self.query_buildid())
            cmd = 'mkdir -p %s' % (aus_current_upload_dir,)
            self.info("debug, normally would run: %s" % (
                str(base_ssh_cmd + cmd)))
            # XXX
            # self.retry(self.run_command, args=(base_ssh_cmd + cmd,))
            # Create remote empty complete/partial snippets for current
            # build.  Also touch the remote platform dir to defeat NFS
            # caching on the AUS webheads.
            self.info("creating empty snippets")
            cmd = 'touch %s/complete.txt %s/partial.txt %s' % (
                aus_current_upload_dir, aus_current_upload_dir,
                root_aus_full_dir
            )
            self.info("debug, normally would run: %s" % (
                str(base_ssh_cmd + cmd)))
            # XXX
            # self.retry(self.run_command, args=(base_ssh_cmd + cmd,))
        #####

        ##### submit balrog update steps
        if c['balrog_api_root']:
            self._submit_balrog_updates()
        #####

    # # TODO trigger other schedulers (if any) I think this may be l10n nightly
    # # builders when we do nightly builds here. This will need to be
    # # done from the master in SigningScript/Script factory

    # TODO find out if we need to do this. For nightlies we always start by
    # clobbering the whole work dir anyway so why bother here? Also, it seems
    # weird to ccache -s after rm the build dir anyway?
    # def cleanup(self):
    #     dirs = self.query_abs_dirs()
    #     if not self.query_is_nightly():
    #         self.info("No clean up required for non nightlies.")
    #         return
    #     # TODO find out if we should blow away the whole abs_work_dir
    #     self.rmtree(dirs['abs_src_dir'])

    def enable_ccache(self):
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        cmd = ['ccache', '-s']
        self.run_command(cmd, cwd=dirs['abs_src_dir'], env=env)
