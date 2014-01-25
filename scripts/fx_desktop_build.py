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
    config_file_search_path = [
        '.', os.path.join(sys.path[0], '..', 'configs'),
        os.path.join(sys.path[0], '..', '..', 'configs')
    ]

    build_variants = {
        'asan': 'builds/releng_sub_%s_configs/%s_asan.py',
        'debug': 'builds/releng_sub_%s_configs/%s_debug.py',
        'asan-and-debug': 'builds/releng_sub_%s_configs/%s_asan_and_debug.py',
        'stat-and-debug': 'builds/releng_sub_%s_configs/%s_stat_and_debug.py',
    }
    build_pools = {
        'staging': 'builds/build_pool_specifics.py',
        'preproduction': 'builds/build_pool_specifics.py',
        'production': 'builds/build_pool_specifics.py',
    }

    @classmethod
    def _query_pltfrm_and_bits(cls, target_option, options):
        """ determine platform and bits

        This can be from either from a supplied --platform and --bits
        or parsed from given config file names.
        """
        error_msg = (
            'Whoops!\nYou are trying to passed a valid shortname for '
            '%s. \nHowever, I need to know the %s to find the appropriate '
            'filename. You can tell me by passing:\n\t"%s" or a config '
            'filename via "--config" with %s in it. \nIn either case, these '
            'option arguments must come before --custom-build-variant.'
        )
        current_config_files = options.config_files or []
        if not cls.bits:
            # --bits has not been supplied
            # lets parse given config file names for 32 or 64
            for cfg_file_name in current_config_files:
                if '32' in cfg_file_name:
                    cls.bits = '32'
                    break
                if '64' in cfg_file_name:
                    cls.bits = '64'
                    break
            else:
                sys.exit(error_msg % (target_option, 'bits', '--bits',
                                      '"32" or "64"'))

        if not cls.platform:
            # --platform has not been supplied
            # lets parse given config file names for platform
            for cfg_file_name in current_config_files:
                if 'windows' in cfg_file_name:
                    cls.platform = 'windows'
                if 'mac' in cfg_file_name:
                    cls.platform = 'mac'
                if 'linux' in cfg_file_name:
                    cls.platform = 'linux'
            else:
                sys.exit(error_msg % (target_option, 'platform', '--platform',
                                      '"linux", "windows", or "mac"'))
        return (cls.bits, cls.platform)

    @classmethod
    def set_build_variant(cls, option, opt, value, parser):
        """ sets an extra config file.

        This is done by either taking an existing filepath or by taking a valid
        shortname coupled with known platform/bits.
        """

        prospective_cfg_path = None
        valid_variant_cfg_path = None
        # first let's see if we were given a valid shortname
        if cls.build_variants.get(value):
            bits, pltfrm = cls._query_pltfrm_and_bits(opt, parser.values)
            prospective_cfg_path = cls.build_variants[value] % (pltfrm, bits)
        else:
            # now let's see if we were given a valid pathname
            if os.path.exists(value):
                # no need to search for it, this is a valid abs or relative
                # pathname
                valid_variant_cfg_path = value
            else:
                # this is either an incomplete path or an invalid key in
                # build_variants
                prospective_cfg_path = value

        # last chance. let's search through some paths to see if we can
        # determine a valid path
        for path in cls.config_file_search_path:
            if os.path.exists(os.path.join(path, prospective_cfg_path)):
                # success! we found a config file
                valid_variant_cfg_path = os.path.join(path,
                                                      prospective_cfg_path)
                break

        if not valid_variant_cfg_path:
            # either the value was an indeterminable path or an invalid short
            # name
            sys.exit("Whoops!\n--custom-build-variant was passed but it was "
                     "either not:\n\ta valid shortname: %s \n\ta valid path "
                     "in %s" % (str(cls.build_variants.keys()),
                                str(cls.config_file_search_path)))
        parser.values.config_files.append(valid_variant_cfg_path)
        option.dest = valid_variant_cfg_path

    @classmethod
    def set_build_pool(cls, option, opt, value, parser):


    @classmethod
    def set_build_branch(cls, option, opt, value, parser):
        # TODO

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
            "help": "Sets the platform we are running this against"
                    "valid values: 'windows', 'mac', 'linux'"}
         ],
        [['--bits'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_bits,
            "type": "string",
            "dest": "bits",
            "help": "Sets which bits we are building this against"
                    "valid values: '32', '64'"}
         ],
        [['--variant-build-cfg'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_variant,
            "type": "string",
            "dest": "build_variant",
            "help": "Sets the build type and will determine appropriate "
                    "additional config to use. Either pass a config path "
                    " or use a valid shortname from: "
                    "%s " % (FxBuildOptionParser.build_variants.keys(),)}
         ],
        [['--pool-build-cfg'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_pool,
            "type": "string",
            "dest": "build_pool",
            "help": "This sets whether we want to use staging, preproduction, "
                    "or production keys/values. The keys/values for this are "
                    "in configs/building/pool_specifics.py"}
         ],
        [['--branch-build-cfg'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_branch,
            "type": "string",
            "dest": "branch",
            "help": "Sets the repo branch being used and if there is a match "
                    "in 'configs/building/branch_specifics.py', add that to "
                    "the config."}
         ],
        [['--enable-pgo'], {
            "action": "store_true",
            "dest": "pgo_build",
            "default": False,
            "help": "Sets the build to run in PGO mode"}
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
