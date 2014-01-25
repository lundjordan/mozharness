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
    build_variants = {
        'asan': 'builds/releng_sub_%s_configs/%s_asan.py',
        'debug': 'builds/releng_sub_%s_configs/%s_debug.py',
        'asan-and-debug': 'builds/releng_sub_%s_configs/%s_asan_and_debug.py',
        'stat-and-debug': 'builds/releng_sub_%s_configs/%s_stat_and_debug.py',
    }

    @classmethod
    def _query_pltfrm_and_bits(cls, target_option, options):
        # this method will inspect the config file path and determine the
        # platform and bits being used. It is for releng configs only
        # error_msg = (
        #     Whoops! \nI noticed you requested a custom build variant but I can
        #     not determine the appropriate filename. You can either pass an
        #     existing relative path or else a valid 'short name'. If you use a short name, say 'asan', I will need to 
        #     trying to find the appropriate config to use but I need to know
        #     what platform and bits you want to run this with.\nThis is what I
        #     was able to find: %s\nOne way I can determine this is through
        #     parsing the main config file passed with --config.\nFor
        #     platform, the config filename must contain mac, windows, or linux.
        #     For bits, it needs 32 or 64. \neg:
        #     builds/releng_base_linux_64_builds.py. \nAlternatively, you can pass
        #     --platform and --bits with the appropriate values. Either way, for now you
        #     must pass these before --custom-build-variant. Unfortunately,
        #     order matters for now.

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
    def set_build_variant(cls, option, opt, value, parser):
        """ sets an extra config file.

        This is done by either taking an existing filepath or by taking a valid
        shortname coupled with known platform/bits.
        """

        build_variant_cfg_path = None
        search_path = [
            '.', os.path.join(sys.path[0], '..', 'configs'),
            os.path.join(sys.path[0], '..', '..', 'configs')
        ]
        # first see if the value passed is a valid path
        if os.path.exists(value):
            build_variant_cfg_path = value
        else:
            for path in search_path:
                if os.path.exists(os.path.join(path, file_name)):
                    build_variant_cfg_path = os.path.join(path, file_name)
                    break
            else:
                if cls.build_variants.get(value):
                    # TODO query platform and bits
                    bits, pltfrm = cls._query_pltfrm_and_bits(opt,
                                                              parser.values)
                    config = cls.build_variants.get(value, '') % (pltfrm, bits)
                    pass
                    # TODO if not platform and bits exit with requirement msg
        if not build_variant_cfg_path:
            # either couldn't determine the file name or used an invalid
            # short name
            # TODO exit with requirement msg
        # TODO save build_variant_cfg_path to dest and config_files

        #     Whoops! \nI noticed you requested a custom build variant but I can
        #     not determine the appropriate filename. You can either pass an
        #     an existing file path 
                ""


        bits, pltfrm = cls._query_pltfrm_and_bits(opt, parser.values)
        config = cls.build_variants.get(value, '') % (pltfrm, bits)
        parser.values.config_files.append(config)
        option.dest = value

    @classmethod
    def set_platform(cls, option, opt, value, parser):
        cls.platform = option.dest = value

    @classmethod
    def set_bits(cls, option, opt, value, parser):
        cls.bits = option.dest = value


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
        [['--platform'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_platform,
            "type": "string",
            "dest": "platform",
            "help": "Sets the platform we are running this against."}
         ],
        [['--bits'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_bits,
            "type": "string",
            "dest": "bits",
            "help": "Sets whether we want a 32 or 64 run of this."}
         ],
        [['--custom-build-variant'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_variant,
            "type": "string",
            "dest": "build_variant",
            "help": "Sets the build type and will determine appropriate "
                    "additional config to use. Examples include: "
                    "%s " % (FxBuildOptionParser.build_variants.keys(),)}
         ],
        [['--enable-pgo'], {
            "action": "store_true",
            "dest": "pgo_build",
            "default": False,
            "help": "Sets the build to run in PGO mode"}
         ],
        [['--build-pool-type'], {
            "action": "store",
            "dest": "build_pool",
            "help": "This sets whether we want to use staging, preproduction, "
                    "or production keys/values. The keys/values for this are "
                    "in configs/building/pool_specifics.py"}
         ],
        [['--branch'], {
            "action": "store",
            "dest": "branch",
            "help": "Sets the repo branch being used and if a match in "
                    "configs/building/branch_specifics.py is found, use that"
                    " config."}
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
                'generate-build-props',
                'generate-build-stats',
                'symbols',
                'packages',
                'upload',
                'sendchanges',
                'pretty-names',
                'check-l10n',
                'check-test',
                'update',
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
                # and whether or not this is a nightly build
                "create_snippets": False,
                "create_partial": False,
                # We have "platform_supports_{snippets, partial}" to dictate
                # whether the platform even supports creating_{snippets,
                # partial}. In other words: we create {snippets, partial} if
                # the branch wants it AND the platform supports it. So for eg:
                # For nightlies, the 'mozilla-central' branch may set
                # create_snippets to true but if it's a linux asan platform,
                # platform_supports_snippets will be False
                "platform_supports_snippets": True,
                "platform_supports_partials": True,
                'complete_mar_pattern': '*.complete.mar',
                'partial_mar_pattern': '*.partial.*.mar',
                # if nightly and our platform is not an ASAN or Stat Analysis
                # variant, use --release-to-latest in post upload cmd
                'platform_supports_post_upload_to_latest': True,
                'aus2_base_upload_dir': '/opt/aus2/incoming/2/Firefox',
                'balrog_credentials_file': 'BuildSlaves.py',
            }
        }
        super(FxDesktopBuild, self).__init__(**basescript_kwargs)
        # TODO epoch is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time this should be
        # (seems unnecessary as a script arg: --build-starttime)
        self.epoch_timestamp = int(time.mktime(datetime.now().timetuple()))
        self.branch = self.config.get('branch')
        self.bits = self.config.get('bits')
        self.buildid = None
        self.builduid = None
        self.repo_path = None
        self.objdir = None

    def _pre_config_lock(self, rw_config):
        """grab buildbot props if we are running this in automation"""
        ### set the branch and platform
        c = self.config
        if c['is_automation']:
            # parse buildbot config and add it to self.config
            self.info("We are running this in buildbot, grab the build props")
            self.read_buildbot_config()
        ###

        ### load branch specifics, if any
        branch_configs = self.parse_config_file('builds/branch_specifics.py')
        if branch_configs[self.branch]:
            self.info('Branch found in file: "builds/branch_specifics.py". '
                      'Updating self.config with keys/values under '
                      'branch: "%s".' % (self.branch,))
            self.config.update(branch_configs[self.branch])
        ###

        ### load build pool specifics, if any
        build_pool_configs = self.parse_config_file(
            'builds/build_pool_specifics.py'
        )
        if build_pool_configs[c['build_pool']]:
            self.info(
                'Build pool found in file: "builds/build_pool_specifics.py". '
                'Updating self.config with keys/values under build pool: '
                '"%s".' % (c['build_pool'],)
            )
            self.config.update(build_pool_configs[c['build_pool']])
        ###

    # helpers

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(FxDesktopBuild, self).query_abs_dirs()

        dirs = {
            # BuildFactories in factory.py refer to a 'build' dir on the slave.
            # This contains all the source code/objdir to compile.  However,
            # there is already a build dir in mozharness for every mh run. The
            # 'build' that factory refers to I named: 'source' so
            # there is a seperation in mh.  for example, rather than having
            # '{mozharness}/build/build/', I have '{mozharness}/build/source/'
            'abs_src_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'source'),
            'abs_obj_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'source',
                                        self._query_objdir()),
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
