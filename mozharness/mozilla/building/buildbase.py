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
import json

import os
import pprint
import subprocess
import time
import uuid
import copy
import glob
from itertools import chain

# import the power of mozharness ;)
import sys
from datetime import datetime
from mozharness.base.config import BaseConfig, parse_config_file
from mozharness.base.script import PostScriptRun
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import BuildbotMixin, TBPL_STATUS_DICT
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.signing import SigningMixin
from mozharness.mozilla.mock import ERROR_MSGS as MOCK_ERROR_MSGS
from mozharness.mozilla.buildbot import TBPL_FAILURE

MISSING_CFG_KEY_MSG = "The key '%s' could not be determined \
Please add this to your config."

ERROR_MSGS = {
    'undetermined_repo_path': 'The repo could not be determined. \
Please make sure that either "repo" is in your config or, if \
you are running this in buildbot, "repo_path" is in your buildbot_config.',
    'comments_undetermined': '"comments" could not be determined. This may be \
because it was a forced build.',
    'src_mozconfig_path_not_found': '"abs_src_mozconfig" path could not be \
determined. Please make sure it is a valid path off of "abs_src_dir"',
    'tooltool_manifest_undetermined': '"tooltool_manifest_src" not set, \
Skipping run_tooltool...',
}
ERROR_MSGS.update(MOCK_ERROR_MSGS)


class BuildingConfig(BaseConfig):
    # TODO add nosetests for this class
    def get_cfgs_from_files(self, all_config_files, parser):
        """ create a config based upon config files passed

        This is class specific. It recognizes certain config files
        by knowing how to combine them in an organized hierarchy
        """
        # override from BaseConfig

        # this is what we will return. It will represent each config
        # file name and its associated dict
        # eg ('builds/branch_specifics.py', {'foo': 'bar'})
        all_config_dicts = []
        # important config files
        variant_cfg_file = branch_cfg_file = pool_cfg_file = ''

        # we want to make the order in which the options were given
        # not matter. ie: you can supply --branch before --build-pool
        # or vice versa and the hierarchy will not be different

        #### The order from highest precedence to lowest is:
        ## There can only be one of these...
        # 1) build_pool: this can be either staging, pre-prod, and prod cfgs
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
                if cf == BuildOptionParser.build_pools[parser.build_pool]:
                    pool_cfg_file = all_config_files[i]

            if cf == BuildOptionParser.branch_cfg_file:
                branch_cfg_file = all_config_files[i]

            if cf == parser.build_variant:
                variant_cfg_file = all_config_files[i]

        # now remove these from the list if there was any.
        # we couldn't pop() these in the above loop as mutating a list while
        # iterating through it causes spurious results :)
        for cf in [pool_cfg_file, branch_cfg_file, variant_cfg_file]:
            if cf:
                all_config_files.remove(cf)

        # now let's update config with the remaining config files.
        # this functionality is the same as the base class
        all_config_dicts.extend(
            super(BuildingConfig, self).get_cfgs_from_files(all_config_files,
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
                all_config_dicts.append(
                    (branch_cfg_file, branch_configs[parser.branch])
                )
        if pool_cfg_file:
            # take only the specific pool. If we are here, the pool
            # must be present
            build_pool_configs = parse_config_file(pool_cfg_file)
            all_config_dicts.append(
                (pool_cfg_file, build_pool_configs[parser.build_pool])
            )
        return all_config_dicts


# noinspection PyUnusedLocal
class BuildOptionParser(object):
    # TODO add nosetests for this class
    platform = None
    bits = None
    config_file_search_path = [
        '.', os.path.join(sys.path[0], '..', 'configs'),
        os.path.join(sys.path[0], '..', '..', 'configs')
    ]

    # add to this list and you can automagically do things like
    # --custom-build-variant non-unified
    # and the script will pull up the appropriate path for the config
    # against the current platform and bits.
    # *It will warn and fail if there is not a config for the current
    # platform/bits
    build_variants = {
        'asan': 'builds/releng_sub_%s_configs/%s_asan.py',
        'debug': 'builds/releng_sub_%s_configs/%s_debug.py',
        'asan-and-debug': 'builds/releng_sub_%s_configs/%s_asan_and_debug.py',
        'stat-and-debug': 'builds/releng_sub_%s_configs/%s_stat_and_debug.py',
        'non-unified': 'builds/releng_sub_%s_configs/%s_non_unified.py',
        'debug-and-non-unified':
                'builds/releng_sub_%s_configs/%s_debug_and_non_unified.py',
    }
    build_pools = {
        'staging': 'builds/build_pool_specifics.py',
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
        return cls.bits, cls.platform

    @classmethod
    def set_build_variant(cls, option, opt, value, parser):
        """ sets an extra config file.

        This is done by either taking an existing filepath or by taking a valid
        shortname coupled with known platform/bits.
        """

        valid_variant_cfg_path = None
        # first let's see if we were given a valid short-name
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
        setattr(parser.values, option.dest, value)  # the pool

    @classmethod
    def set_build_pool(cls, option, opt, value, parser):
        if cls.build_pools.get(value):
            # first let's add the build pool file where there may be pool
            # specific keys/values. Then let's store the pool name
            parser.values.config_files.append(cls.build_pools[value])
            setattr(parser.values, option.dest, value)  # the pool
        else:
            sys.exit(
                "Whoops!\n--build-pool was passed with '%s' but only "
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


# this global depends on BuildOptionParser and therefore can not go at the
# top of the file
BUILD_BASE_CONFIG_OPTIONS = [
    [['--developer-run', '--skip-buildbot-actions'], {
        "action": "store_false",
        "dest": "is_automation",
        "default": True,
        "help": "If this is running outside of Mozilla's build"
                "infrastructure, use this option. It ignores actions"
                "that are not needed and adds config checks."}],
    [['--platform'], {
        "action": "callback",
        "callback": BuildOptionParser.set_platform,
        "type": "string",
        "dest": "platform",
        "help": "Sets the platform we are running this against"
                " valid values: 'windows', 'mac', 'linux'"}],
    [['--bits'], {
        "action": "callback",
        "callback": BuildOptionParser.set_bits,
        "type": "string",
        "dest": "bits",
        "help": "Sets which bits we are building this against"
                " valid values: '32', '64'"}],
    [['--custom-build-variant-cfg'], {
        "action": "callback",
        "callback": BuildOptionParser.set_build_variant,
        "type": "string",
        "dest": "build_variant",
        "help": "Sets the build type and will determine appropriate"
                " additional config to use. Either pass a config path"
                " or use a valid shortname from: "
                "%s" % (BuildOptionParser.build_variants.keys(),)}],
    [['--build-pool'], {
        "action": "callback",
        "callback": BuildOptionParser.set_build_pool,
        "type": "string",
        "dest": "build_pool",
        "help": "This will update the config with specific pool"
                " environment keys/values. The dicts for this are"
                " in %s\nValid values: staging or"
                " production" % ('builds/build_pool_specifics.py',)}],
    [['--branch'], {
        "action": "callback",
        "callback": BuildOptionParser.set_build_branch,
        "type": "string",
        "dest": "branch",
        "help": "This sets the branch we will be building this for."
                " If this branch is in branch_specifics.py, update our"
                " config with specific keys/values from that. See"
                " %s for possibilites" % (
                    BuildOptionParser.branch_cfg_file,
                )}],
    [['--enable-pgo'], {
        "action": "store_true",
        "dest": "pgo_build",
        "default": False,
        "help": "Sets the build to run in PGO mode"}],
    [['--enable-nightly'], {
        "action": "store_true",
        "dest": "nightly_build",
        "default": False,
        "help": "Sets the build to run in nightly mode"}],
    [['--who'], {
        "dest": "who",
        "default": '',
        "help": "stores who made the created the buildbot change."}],

]


class BuildScript(BuildbotMixin, PurgeMixin, MockMixin,
                  SigningMixin, MercurialScript):
    def __init__(self, **kwargs):
        # objdir is referenced in _query_abs_dirs() so let's make sure we
        # have that attribute before calling BaseScript.__init__
        self.objdir = None
        super(BuildScript, self).__init__(**kwargs)
        # epoch is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time it would be if it was
        # done through MBF.
        # TODO find out if that time diff matters or if we just use it to
        # separate each build
        self.epoch_timestamp = int(time.mktime(datetime.now().timetuple()))
        self.branch = self.config.get('branch')
        self.stage_platform = self.config.get('stage_platform')
        if not self.branch or not self.stage_platform:
            if not self.branch:
                self.error("'branch' not determined and is required")
            if not self.stage_platform:
                self.error("'stage_platform' not determined and is required")
            self.fatal("Please add missing items to your config")
        self.repo_path = None
        self.buildid = None
        self.builduid = None
        self.query_buildid()  # sets self.buildid
        self.query_builduid()  # sets self.builduid

    def _pre_config_lock(self, rw_config):
        c = self.config
        cfg_files_and_dicts = rw_config.all_cfg_files_and_dicts
        build_pool = c.get('build_pool', '')
        build_variant = c.get('build_variant', '')
        variant_cfg = ''
        if build_variant:
            variant_cfg = BuildOptionParser.build_variants[build_variant] % (
                BuildOptionParser.platform,
                BuildOptionParser.bits
            )
        build_pool_cfg = BuildOptionParser.build_pools.get(build_pool)
        branch_cfg = BuildOptionParser.branch_cfg_file

        cfg_match_msg = "Script was ran with '%(option)s %(type)s' and \
'%(type)s' matches a key in '%(type_config_file)s'. Updating self.config with \
items from that key's value."
        pf_override_msg = "The branch '%(branch)s' has custom behavior for the \
platform '%(platform)s'. Updating self.config with the following from \
'platform_overrides' found in '%(pf_cfg_file)s':"

        for i, (target_file, target_dict) in enumerate(cfg_files_and_dicts):
            if branch_cfg and branch_cfg in target_file:
                self.info(
                    cfg_match_msg % {
                        'option': '--branch',
                        'type': c['branch'],
                        'type_config_file': BuildOptionParser.branch_cfg_file
                    }
                )
            if build_pool_cfg and build_pool_cfg in target_file:
                self.info(
                    cfg_match_msg % {
                        'option': '--build-pool',
                        'type': build_pool,
                        'type_config_file': BuildOptionParser.build_pools[
                            build_pool
                        ]
                    }
                )
            if variant_cfg and variant_cfg in target_file:
                self.info(
                    cfg_match_msg % {
                        'option': '--custom-build-variant-cfg',
                        'type': build_variant,
                        'type_config_file': variant_cfg,
                    }
                )
        if c.get("platform_overrides"):
            if c['stage_platform'] in c['platform_overrides'].keys():
                self.info(
                    pf_override_msg % {
                        'branch': c['branch'],
                        'platform': c['stage_platform'],
                        'pf_cfg_file': BuildOptionParser.branch_cfg_file
                    }
                )
                branch_pf_overrides = c['platform_overrides'][
                    c['stage_platform']
                ]
                self.info(pprint.pformat(branch_pf_overrides))
                c.update(branch_pf_overrides)
        self.info('To generate a config file based upon options passed and '
                  'config files used, run script as before but extend options '
                  'with "--dump-config"')
        self.info('For a diff of where self.config got its items, '
                  'run the script again as before but extend options with: '
                  '"--dump-config-hierarchy"')
        self.info("Both --dump-config and --dump-config-hierarchy don't "
                  "actually run any actions.")

    def _assert_cfg_valid_for_action(self, dependencies, action):
        """ assert dependency keys are in config for given action.

        Takes a list of dependencies and ensures that each have an
        assoctiated key in the config. Displays error messages as
        appropriate.

        """
        # TODO add type and value checking, not just keys
        # TODO solution should adhere to: bug 699343
        # TODO add this to BaseScript when the above is done
        # for now, let's just use this as a way to save typing...
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

    def _query_build_prop_from_app_ini(self, prop, app_ini_path=None):
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config',
                                               'printconfigsetting.py')
        if not app_ini_path:
            # set the default
            app_ini_path = dirs['abs_app_ini_path']
        if (os.path.exists(print_conf_setting_path) and
                os.path.exists(app_ini_path)):
            cmd = [
                'python', print_conf_setting_path, app_ini_path,
                'App', prop
            ]
            return self.get_output_from_command(cmd, cwd=dirs['base_work_dir'])
        else:
            return ''

    def query_builduid(self):
        c = self.config
        if self.builduid:
            return self.builduid
        in_buildbot_props = False
        if c.get("is_automation"):
            if self.buildbot_config['properties'].get('builduid'):
                in_buildbot_props = True

        # let's see if it's in buildbot_properties
        if in_buildbot_props:
            self.info("Determining builduid from buildbot properties")
            self.builduid = self.buildbot_config['properties']['builduid']
        else:
            self.info("Creating builduid through uuid hex")
            self.builduid = uuid.uuid4().hex

        if self.builduid:
            if c.get('is_automation') and not in_buildbot_props:
                self.set_buildbot_property('builduid',
                                           self.buildid,
                                           write_to_file=True)
        else:
            # something went horribly wrong
            self.fatal("Could not determine builduid!")
        return self.builduid

    def query_buildid(self):
        c = self.config
        if self.buildid:
            return self.buildid
        in_buildbot_props = False
        if c.get("is_automation"):
            if self.buildbot_config['properties'].get('buildid'):
                in_buildbot_props = True

        # first let's see if we have already built ff
        # in which case we would have a buildid
        if self._query_build_prop_from_app_ini('BuildID'):
            self.info("Determining buildid from application.ini")
            self.buildid = self._query_build_prop_from_app_ini('BuildID')
        # now let's see if it's in buildbot_properties
        elif in_buildbot_props:
            self.info("Determining buildid from buildbot properties")
            self.buildid = self.buildbot_config['properties']['buildid']
        else:
            # finally, let's resort to making a buildid this will happen when
            #  buildbot has not made one, and we are running this script for
            # the first time in a clean clobbered state
            self.info("Creating buildid through current time")
            self.buildid = time.strftime("%Y%m%d%H%M%S",
                                         time.localtime(time.time()))
        if self.buildid:
            if c.get('is_automation') and not in_buildbot_props:
                self.set_buildbot_property('buildid',
                                           self.buildid,
                                           write_to_file=True)
        else:
            # something went horribly wrong
            self.fatal("Could not determine Buildid!")

        return self.buildid

    def _query_objdir(self):
        if self.objdir:
            return self.objdir

        if not self.config.get('objdir'):
            return self.fatal(MISSING_CFG_KEY_MSG % ('objdir',))
        self.objdir = self.config['objdir']
        return self.objdir

    def _query_repo(self):
        if self.repo_path:
            return self.repo_path
        c = self.config

        # unlike b2g, we actually supply the repo in mozharness so if it's in
        #  the config, we use that (automation does not require it in
        # buildbot props)
        if not c.get('repo_path'):
            repo_path = 'projects/%s' % (self.branch,)
            self.info(
                "repo_path not in config. Using '%s' instead" % (repo_path,)
            )
        else:
            repo_path = c['repo_path']
        self.repo_path = '%s/%s' % (c['repo_base'], repo_path,)
        return self.repo_path

    def _skip_buildbot_specific_action(self):
        """ ignore actions from buildbot's infra."""
        self.info("This action is specific to buildbot's infrastructure")
        self.info("Skipping......")
        return

    def query_build_env(self, skip_keys=None, replace_dict=None, **kwargs):
        c = self.config
        if skip_keys is None:
            skip_keys = []

        if not replace_dict:
            replace_dict = {}
        # now let's grab the right host based off staging/production
        # symbol_server_host is defined in build_pool_specifics.py
        replace_dict.update({"symbol_server_host": c['symbol_server_host']})

        # let's evoke the base query_env and make a copy of it
        # as we don't always want every key below added to the same dict
        env = copy.deepcopy(
            super(BuildScript, self).query_env(replace_dict=replace_dict,
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

        if self.config.get('pgo_build'):
            env['IS_PGO'] = '1'

        if c.get('enable_signing') and 'MOZ_SIGN_CMD' not in skip_keys:
            moz_sign_cmd = self.query_moz_sign_cmd()
            env["MOZ_SIGN_CMD"] = subprocess.list2cmdline(moz_sign_cmd)
        else:
            # so SigningScriptFactory (what calls mozharness script
            # from buildbot) assigns  MOZ_SIGN_CMD but does so incorrectly
            # for desktop builds. Also, sometimes like for make l10n check,
            # we don't actually want it in the env
            if env.get("MOZ_SIGN_CMD"):
                del env["MOZ_SIGN_CMD"]

        # we can't make env an attribute of self because env can change on
        # every call for reasons like MOZ_SIGN_CMD
        return env

    def _ccache_z(self):
        """clear ccache stats."""
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        if os.path.exists(dirs['abs_src_dir']):
            self.run_command(command=['ccache', '-z'],
                             cwd=dirs['abs_src_dir'],
                             env=env)

    def _rm_old_package(self):
        """rm the old package."""
        c = self.config
        dirs = self.query_abs_dirs()
        old_package_paths = []
        old_package_patterns = c.get('old_packages')

        self.info("removing old packages...")
        if os.path.exists(dirs['abs_obj_dir']):
            for product in old_package_patterns:
                old_package_paths.extend(
                    glob.glob(product % {"objdir": dirs['abs_obj_dir']})
                )
        if old_package_paths:
            for package_path in old_package_paths:
                self.rmtree(package_path)
        else:
            self.info("There wasn't any old packages to remove.")

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
            self.info("mozconfig content:")
            with open(abs_src_mozconfig) as mozconfig:
                next(mozconfig)
                for line in mozconfig:
                    self.info(line)
        else:
            self.fatal("To build, you must supply a mozconfig from inside the "
                       "tree to use use. Please provide the path in your "
                       "config via 'src_mozconfig'")

    # TODO add this or merge to ToolToolMixin
    def _run_tooltool(self):
        self._assert_cfg_valid_for_action(
            ['tooltool_script', 'tooltool_bootstrap', 'tooltool_url'],
            'build'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('tooltool_manifest_src'):
            return self.warning(ERROR_MSGS['tooltool_manifest_undetermined'])
        fetch_script_path = os.path.join(dirs['abs_tools_dir'],
                                         'scripts/tooltool/tooltool_wrapper.sh')
        tooltool_manifest_path = os.path.join(dirs['abs_src_dir'],
                                              c['tooltool_manifest_src'])
        cmd = [
            'sh',
            fetch_script_path,
            tooltool_manifest_path,
            c['tooltool_url'],
            c['tooltool_bootstrap'],
        ]
        cmd.extend(c['tooltool_script'])
        self.info(str(cmd))
        self.run_command(cmd, cwd=dirs['abs_src_dir'])

    def query_revision(self, source_path=None):
        """ returns the revision of the build

         first will look for it in buildbot_properties and then in
         buildbot_config. Failing that, it will actually poll the source of
         the repo if it exists yet.
        """
        # this is basically a copy from b2g_build.py
        # TODO get b2g_build.py to use this version of query_revision
        if 'revision' in self.buildbot_properties:
            return self.buildbot_properties['revision']

        if self.buildbot_config and self.buildbot_config.get('revision'):
            return self.buildbot_config['revision']

        if self.buildbot_config and self.buildbot_config.get('sourcestamp'):
            return self.buildbot_config['sourcestamp']['revision']

        if not source_path:
            dirs = self.query_abs_dirs()
            source_path = dirs['abs_src_dir']  # let's take the default

        # Look at what we have checked out
        if os.path.exists(source_path):
            hg = self.query_exe('hg', return_type='list')
            return self.get_output_from_command(
                hg + ['parent', '--template', '{node|short}'], cwd=source_path
            )

        return None

    def _checkout_source(self):
        """use vcs_checkout to grab source needed for build."""
        c = self.config
        dirs = self.query_abs_dirs()
        repo = self._query_repo()
        vcs_checkout_kwargs = {
            'repo': repo,
            'dest': dirs['abs_src_dir'],
            'revision': self.query_revision(),
            'env': self.query_build_env()
        }
        if c.get('clone_by_revision'):
            vcs_checkout_kwargs['clone_by_revision'] = True

        if c.get('clone_with_purge'):
            vcs_checkout_kwargs['clone_with_purge'] = True
        rev = self.vcs_checkout(**vcs_checkout_kwargs)
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

    def _submit_balrog_updates(self, balrog_type='nightly'):
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
                                         "balrog_props.json")
        balrog_submitter_path = os.path.join(dirs['abs_tools_dir'],
                                             'scripts',
                                             'updates',
                                             'balrog-submitter.py')
        self.set_buildbot_property(
            'hashType', c.get('hash_type', 'sha512'), write_to_file=True
        )
        all_current_props = dict(
            chain(self.buildbot_config['properties'].items(),
                  self.buildbot_properties.items())
        )
        self.info("Dumping buildbot properties to %s." % balrog_props_path)
        balrog_props = dict(properties=all_current_props)
        self.dump_config(balrog_props_path, balrog_props)
        cmd = [
            self.query_exe('python'),
            balrog_submitter_path,
            '--build-properties', balrog_props_path,
            '--api-root', c['balrog_api_root'],
            '--username', c['balrog_username'],
            '-t', balrog_type, '--verbose',
        ]
        if c['balrog_credentials_file']:
            self.info("Using Balrog credential file...")
            abs_balrog_cred_file = os.path.join(
                c['base_work_dir'], c['balrog_credentials_file']
            )
            if not abs_balrog_cred_file:
                self.fatal("credential file given but doesn't exist!"
                           " Path given: %s" % abs_balrog_cred_file)
            cmd.extend(['--credentials-file', abs_balrog_cred_file])
        else:
            self.fatal("Balrog requires a credential file. Pease add the"
                       " path to your config via: 'balrog_credentials_file'")
        self.info("Submitting Balrog updates...")
        self.retry(
            self.run_command, args=(cmd,),
            kwargs={
                'halt_on_failure': True,
                'fatal_exit_code': 3,
            }
        )

    def clone_tools(self):
        """clones the tools repo."""
        self._assert_cfg_valid_for_action(['tools_repo'], 'clone_tools')
        c = self.config
        dirs = self.query_abs_dirs()
        repo = {
            'repo': c['tools_repo'],
            'vcs': 'hg',
            'dest': dirs['abs_tools_dir'],
            'output_timeout': 1200,
        }
        self.vcs_checkout(**repo)

    def _create_mozbuild_dir(self, mozbuild_path=None):
        if not mozbuild_path:
            env = self.query_build_env()
            mozbuild_path = env.get('MOZBUILD_STATE_PATH')
        if mozbuild_path:
            self.mkdir_p(os.path.join(self.query_abs_dirs()['abs_src_dir'],
                                      '.mozbuild'))
        else:
            self.warning("mozbuild_path could not be determined. skipping "
                         "creating it.")

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
        self._create_mozbuild_dir()

    def build(self):
        """build application."""
        self.return_code = self.run_command_m(
            command=['./mach', 'build'], cwd=self.query_abs_dirs()['abs_src_dir'],
            env=self.query_build_env()
        )

    def postflight_build(self, console_output=True):
        """grab properties set by mach build."""
        mach_properties_path = os.path.join(
            self.query_abs_dirs()['abs_work_dir'], 'build_properties.json'
        )
        if os.path.exists(mach_properties_path):
            with open(mach_properties_path) as build_property_file:
                build_props = json.load(build_property_file)
                if console_output:
                    self.info("Properties set from 'mach build'")
                    pprint.pformat(build_props)
            for key, prop in build_props.iteritems():
                self.set_buildbot_property(key, prop, write_to_file=True)
        else:
            self.warning("'mach build' did not set any properties from build.")

    def update(self):
        """ submit balrog update steps. """
        c = self.config
        if not self.query_is_nightly():
            self.info("Skipping action because this action is only done for "
                      "nightlies...")
            return

        self.info("SKIPPING UNTIL WE ADD MAR GEN LOGIC")
        # if c['balrog_api_root']:
        #     self._submit_balrog_updates()

    def _post_fatal(self, message=None, exit_code=None):
        # until this script has more defined return_codes, let's make sure
        # that we at least set the return_code to a failure for things like
        # _summarize()
        self.return_code = 2

    @PostScriptRun
    def _summarize(self):
        if self.return_code != 0:
            # TODO this will need some work. Once we define various return
            # codes and correlate tbpl levels against it, we can have more
            # definitions for tbpl status
            # bug 985068 should lay the plumbing down for this work
            self.worst_buildbot_status = self.worst_level(
                TBPL_FAILURE, self.worst_buildbot_status, TBPL_STATUS_DICT
            )
        self.buildbot_status(self.worst_buildbot_status)
        self.summary()
