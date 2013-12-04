#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""fx_nightly_build.py.

script harness to build nightly firefox within Mozilla's build environment
and developer machines alike

author: Jordan Lund

"""

import sys
import os
import time
from datetime import datetime

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import mozharness ;)
from mozharness.mozilla.building.buildbase import BuildingMixin
from mozharness.base.vcs.vcsbase import MercurialScript


class FxBuildOptionParser(object):
    platform = None
    bits = None
    build_types = {
        'asan': 'builds/releng_sub_%s_configs/%s_asan.py',
        'debug': 'builds/releng_sub_%s_configs/%s_debug.py',
        'asan-and-debug': 'builds/releng_sub_%s_configs/%s_asan_and_debug.py',
        'stat-and-debug': 'builds/releng_sub_%s_configs/%s_stat_and_debug.py',
    }

    @classmethod
    def _query_pltfrm_and_bits(cls, target_option, options):
        # this method will inspect the config file path and determine the
        # platform and bits being used. It is for releng configs only

        # let's discover what platform we are using
        if not cls.bits:
            if '32' in options.config_files[0]:
                cls.bits = '32'
            elif '64' in options.config_files[0]:
                cls.bits = '64'
            else:
                sys.exit('Could not determine bits to use. '
                         'Please ensure the "--config" has "32" or "64" in '
                         'it and is specified prior to: %s' % (target_option,))
        # now let's discover what platform we are using
        if not cls.platform:
            if 'windows' in options.config_files[0]:
                cls.platform = 'windows'
            elif 'mac' in options.config_files[0]:
                cls.platform = 'mac'
            elif 'linux' in options.config_files[0]:
                cls.platform = 'linux'
            else:
                sys.exit("Couldn't determine platform. Please ensure "
                         'the "--config" has "windows", "mac", or "linux" in '
                         'it and is specified prior to: %s' % (target_option,))
        return (cls.bits, cls.platform)

    @classmethod
    def set_build_type(cls, option, opt, value, parser):
        bits, pltfrm = cls._query_pltfrm_and_bits(opt, parser.values)
        config = cls.build_types.get(value, '') % (pltfrm, bits)
        parser.values.config_files.append(config)
        option.dest = value


class FxDesktopBuild(BuildingMixin, MercurialScript, object):
    config_options = [
        [['--developer-run', '--skip-buildbot-actions'], {
            "action": "store_false",
            "dest": "is_automation",
            "default": True,
            "help": "If this is running outside of Mozilla's build"
                    "infrastructure, use this option. It ignores actions"
                    "that are not needed and adds config checks."}
         ],
        [['--custom-build-type'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_type,
            "type": "string",
            "dest": "build_type",
            "help": "Sets the build type and will determine appropriate "
                    "additional config to use. Examples include: "
                    "%s " % (FxBuildOptionParser.build_types.keys(),)}
         ],
        [['--enable-pgo'], {
            "action": "store_true",
            "dest": "pgo_build",
            "default": False,
            "help": "Sets the build to run in PGO mode"}
         ],
        [['--branch'], {
            "action": "store",
            "dest": "branch",
            "help": "Sets the repo branch being used"}
         ],
        [['--platform'], {
            "action": "store",
            "dest": "platform",
            "help": "Sets the platform being used"}
         ],
    ]

    def __init__(self, require_config_file=True):
        basescript_kwargs = {
            'config_options': self.config_options,
            'all_actions': [
                'clobber',
                'pull',
                'setup-mock',
                'build',
                'generate-build-properties',
                'generate-build-stats',
                'make-build-symbols',
                'make-packages',
                'make-upload',
                'test-pretty-names',
                'check-test-complete',
                'enable-ccache',
            ],
            'require_config_file': require_config_file,
            # Default configuration
            'config': {
                "branch_specific_config_file": "builds/branch_specifics.py",
                "pgo_build": False,
                'is_automation': True,
                # create_snippets will be decided by
                # configs/builds/branch_specifics.py
                "create_snippets": False,
                # We have "platform_supports_snippets" to dictate whether the
                # platform even supports creating_snippets. In other words:
                # create snippets if the branch wants it AND the platform
                # supports it So for eg: For nightlies, the 'mozilla-central'
                # branch may set create_snippets to true but if it's a debug
                # platform platform_supports_snippets will be False
                "platform_supports_snippets": True,
            }
        }
        # TODO epoch is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time this should be
        # (seems unnecessary as a script arg: --build-starttime)
        self.epoch_timestamp = int(time.mktime(datetime.now().timetuple()))
        self.repo_path = None
        self.objdir = None
        self.buildid = None
        self.builduid = None
        self.branch = None  # set in pre_config_lock
        super(FxDesktopBuild, self).__init__(**basescript_kwargs)

    def _pre_config_lock(self, rw_config):
        """Validate cfg, parse buildbot props and load branch specifics.

        First, if running through buildbot, add buildbot props to self.config
        Then, if the branch specified is in branch_specifics, add the
        keys/values to self.config for those.
        Finally, validate that the appropriate configs are in
        self.config for actions being run.

        """
        c = self.config
        ### set the branch and platform
        if c['is_automation']:
            # parse buildbot config and add it to self.config
            self.read_buildbot_config()
            self.branch = self.buildbot_config['properties'].get('branch')
            self.platform = self.buildbot_config['properties'].get('platform')
            if not self.branch or not self.platform:
                warn_msg_template = ("Could not determine %s in buildbot props"
                                     ". Falling back to '%s' in self.config.")
                if not self.branch:
                    self.warning(warn_msg_template % ('branch', 'branch'))
                    self.branch = c.get("branch")
                if not self.platform:
                    self.warning(warn_msg_template % ('platform', 'platform'))
                    self.platform = c.get("platform")
        else:  # --developer-run was specified
            self.branch = c.get("branch")
            self.platform = c.get("platform")
        if not self.branch or not self.platform:
            self.fatal("The branch or platorm could not be determined. If this"
                       "is a developer run, you must specify them in your"
                       "config. Branch: %s, Platform: %s" (
                           self.branch or 'undetermined',
                           self.platform or 'undetermined')
                       )
        ###

        ### load branch specifics, if any
        branch_configs = self.parse_config_file('builds/branch_specifics.py')
        if branch_configs[self.branch]:
            self.info('Branch found in file: "builds/branch_specifics.py". '
                      'Updating self.config with keys/values under '
                      'branch: "%s".' % (self.branch,))
            self.config.update(branch_configs[self.branch])
        ###

        # now verify config keys are valid for actions being used this run
        config_dependencies = {
            # key = action, value = list of action's config dependencies
            'setup-mock': ['mock_target'],
            'build': ['ccache_env', 'old_packages', 'mock_target'],
            # 'generate-build-stats': [
            #     'graph_server', 'graph_selector', 'graph_branch', 'base_name'
            # ],
            'make-build-symbols': ['mock_target'],
            'make-packages': ['package_filename', 'mock_target'],
            'make-upload': ['upload_env', 'stage_platform', 'mock_target'],
        }
        for action in self.actions:
            if config_dependencies.get(action):
                self._assert_cfg_valid_for_action(config_dependencies[action],
                                                  action)

    # helpers

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(FxDesktopBuild, self).query_abs_dirs()

        dirs = {
            'abs_src_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'source'),
            'abs_tools_dir': os.path.join(abs_dirs['abs_work_dir'], 'tools'),
        }
        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # Actions {{{2
    # read_buildbot_config in BuildingMixin
    # clobber in BuildingMixin -> PurgeMixin
    # if Linux config:
        # reset_mock in BuildingMixing -> MockMixin
        # setup_mock in BuildingMixing (overrides MockMixin.mock_setup)


if __name__ == '__main__':
    fx_nightly_build = FxDesktopBuild()
    fx_nightly_build.run_and_exit()
