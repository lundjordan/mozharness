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
from mozharness.base.config import BaseConfig
from mozharness.mozilla.building.buildbase import BuildingMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.base.config import parse_config_file


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
    branch_cfg_file = 'builds/branch_specifics.py'

    @classmethod
    def _query_pltfrm_and_bits(cls, target_option, options):
        """ determine platform and bits

        This can be from either from a supplied --platform and --bits
        or parsed from given config file names.
        """
        error_msg = (
            'Whoops!\nYou are trying to pass a shortname for '
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
                    break
                if 'mac' in cfg_file_name:
                    cls.platform = 'mac'
                    break
                if 'linux' in cfg_file_name:
                    cls.platform = 'linux'
                    break
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
            # this is either an incomplete path or an invalid key in
            # build_variants
            prospective_cfg_path = value

        if os.path.exists(prospective_cfg_path):
            # now let's see if we were given a valid pathname
            valid_variant_cfg_path = value
        else:
            # let's take our prospective_cfg_path and see if we can
            # determine an existing file
            for path in cls.config_file_search_path:
                if os.path.exists(os.path.join(path, prospective_cfg_path)):
                    # success! we found a config file
                    valid_variant_cfg_path = os.path.join(path,
                                                          prospective_cfg_path)
                    break

        if not valid_variant_cfg_path:
            # either the value was an indeterminable path or an invalid short
            # name
            sys.exit("Whoops!\n'--custom-build-variant' was passed but an "
                     "appropriate config file could not be determined. Tried "
                     "using: '%s' but it was either not:\n\t-- a valid "
                     "shortname: %s \n\t-- a valid path in %s \n\t-- a "
                     "valid variant for the given platform and bits." % (
                         prospective_cfg_path,
                         str(cls.build_variants.keys()),
                         str(cls.config_file_search_path)))
        parser.values.config_files.append(valid_variant_cfg_path)
        option.dest = valid_variant_cfg_path

    @classmethod
    def set_build_pool(cls, option, opt, value, parser):
        if cls.build_pools.get(value):
            # first let's add the build pool file where there may be pool
            # specific keys/values. Then let's store the pool name
            parser.values.config_files.append(cls.build_pools[value])
            setattr(parser.values, option.dest, value)  # the pool
        else:
            sys.exit(
                "Whoops!\n--build-pool-type was passed with '%s' but only "
                "'%s' are valid options" % (value, str(cls.build_pools.keys()))
            )

    @classmethod
    def set_build_branch(cls, option, opt, value, parser):
        # first let's add the branch_specific file where there may be branch
        # specific keys/values. Then let's store the branch name we are using
        parser.values.config_files.append(cls.branch_cfg_file)
        setattr(parser.values, option.dest, value)  # the branch name

    @classmethod
    def set_platform(cls, option, opt, value, parser):
        cls.platform = value
        setattr(parser.values, option.dest, value)

    @classmethod
    def set_bits(cls, option, opt, value, parser):
        cls.bits = value
        setattr(parser.values, option.dest, value)


class FxBuildConfig(BaseConfig):

    def get_cfgs_from_files(self, all_config_files, parser):
        """ create a config based upon config files passed

        This is class specific. It recognizes certain config files
        by knowing how to combine them in an organized hierarchy
        """
        # overrided from BaseConfig
        # *NOTE the base class of this method supports configs from urls. For
        # the purpose of this script, which does not have to be generic, I am
        # not adding that functionality.

        # this is what we will return. It will represent each config
        # file name and its assoctiated dict
        # eg ('builds/branch_specifics.py', {'foo': 'bar'})
        all_config_dicts = []
        # important config files
        variant_cfg_file = branch_cfg_file = pool_cfg_file = ''

        # we want to make the order in which the options were given
        # not matter. ie: you can supply --branch before --build-pool
        # or vice versa and the hierarchy will not be different

        #### The order from highest presedence to lowest is:
        ## There can only be one of these...
        # 1) build_pool: this can be either staging, preprod, and prod cfgs
        # 2) branch: eg: mozilla-central, cedar, cypress, etc
        # 3) build_variant: these could be known like asan and debug
        #                   or a custom config
        ##
        ## There can be many of these
        # 4) all other configs: these are any configs that are passed with
        #                       --cfg and --opt-cfg. There order is kept in
        #                       which they were passed on the cmd line. This
        #                       behaviour is maintains what happens by default
        #                       in mozharness
        ##
        ####

        # so, let's first assign the configs that hold a known position of
        # importance (1 through 3)
        for i, cf in enumerate(all_config_files):
            if parser.build_pool:
                if cf == FxBuildOptionParser.build_pools[parser.build_pool]:
                    pool_cfg_file = all_config_files[i]

            if cf == FxBuildOptionParser.branch_cfg_file:
                branch_cfg_file = all_config_files[i]

            if cf == parser.build_variant:
                variant_cfg_file = all_config_files[i]

        # now remove these from the list if there was any
        # we couldn't pop() these in the above loop as mutating a list while
        # iterating through it causes spurious results :)
        for cf in [pool_cfg_file, branch_cfg_file, variant_cfg_file]:
            if cf:
                all_config_files.remove(cf)

        # now let's update config with the remaining config files.
        # this functionality is the same as the base class
        all_config_dicts.extend(
            super(FxBuildConfig, self).get_cfgs_from_files(all_config_files,
                                                           parser)
        )

        # stack variant, branch, and pool cfg files on top of that,
        # if they are present, in that order
        if variant_cfg_file:
            # take the whole config
            all_config_dicts.append(
                (variant_cfg_file, parse_config_file(variant_cfg_file))
            )
        if branch_cfg_file:
            # take only the specific branch, if present
            branch_configs = parse_config_file(branch_cfg_file)
            if branch_configs.get(parser.branch or ""):
                print(
                    'Branch found in file: "builds/branch_specifics.py". '
                    'Updating self.config with keys/values under '
                    'branch: "%s".' % (parser.branch,)
                )
                all_config_dicts.append(
                    (branch_cfg_file, branch_configs[parser.branch])
                )
        if pool_cfg_file:
            # take only the specific pool. If we are here, the pool
            # must be present
            build_pool_configs = parse_config_file(pool_cfg_file)
            print(
                'Build pool config found in file: '
                '"builds/build_pool_specifics.py". Updating self.config'
                ' with keys/values under build pool: '
                '"%s".' % (parser.build_pool,)
            )
            all_config_dicts.append(
                (pool_cfg_file, build_pool_configs[parser.build_pool])
            )
        return all_config_dicts


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
        [['--custom-build-variant-cfg'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_variant,
            "type": "string",
            "dest": "build_variant",
            "help": "Sets the build type and will determine appropriate "
                    "additional config to use. Either pass a config path "
                    " or use a valid shortname from: "
                    "%s " % (FxBuildOptionParser.build_variants.keys(),)}
         ],
        [['--build-pool-type'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_pool,
            "type": "string",
            "dest": "build_pool",
            "help": "This will update the config with specific pool "
                    "environment keys/values. The dicts for this are "
                    "in %s\nValid values: staging, preproduction, or "
                    "production" % ('builds/build_pool_specifics.py',)}
         ],
        [['--branch'], {
            "action": "callback",
            "callback": FxBuildOptionParser.set_build_branch,
            "type": "string",
            "dest": "branch",
            "help": "This sets the branch we will be building this for. "
                    "If this branch is in branch_specifics.py, update our "
                    "config with specific keys/values from that. See "
                    "%s for possibilites" % (
                        FxBuildOptionParser.branch_cfg_file,
                    )}
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
        super(FxDesktopBuild, self).__init__(
            config_class=FxBuildConfig, **basescript_kwargs
        )
        # TODO epoch is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time this should be
        # (seems unnecessary as a script arg: --build-starttime)
        self.epoch_timestamp = int(time.mktime(datetime.now().timetuple()))
        self.branch = self.config.get('branch')
        self.bits = self.config.get('bits')
        self.platform = self.config.get('platform')
        if self.bits == '64' and not self.platform.endswith('64'):
            self.platform += '64'
        self.buildid = None
        self.builduid = None
        self.repo_path = None
        self.objdir = None

    def _pre_config_lock(self, rw_config):
        """grab buildbot props if we are running this in automation"""
        c = self.config
        if c['is_automation']:
            # parse buildbot config and add it to self.config
            self.info("We are running this in buildbot, grab the build props")
            self.read_buildbot_config()
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
