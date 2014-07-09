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
import re
from mozharness.base.config import BaseConfig, parse_config_file
from mozharness.base.log import ERROR, OutputParser
from mozharness.base.script import PostScriptRun
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import BuildbotMixin, TBPL_STATUS_DICT, \
    TBPL_EXCEPTION, TBPL_SUCCESS, TBPL_WORST_LEVEL_TUPLE, TBPL_RETRY, \
    EXIT_STATUS_DICT
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.signing import SigningMixin
from mozharness.mozilla.mock import ERROR_MSGS as MOCK_ERROR_MSGS
from mozharness.mozilla.updates.balrog import BalrogMixin

AUTOMATION_EXIT_CODES = EXIT_STATUS_DICT.values()
AUTOMATION_EXIT_CODES.sort()

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


### Output Parsers

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

class MakeUploadOutputParser(OutputParser):
    tbpl_error_list = TBPL_UPLOAD_ERRORS
    # let's create a switch case using name-spaces/dict
    # rather than a long if/else with duplicate code
    property_conditions = [
        # key: property name, value: condition
        ('symbolsUrl', "m.endswith('crashreporter-symbols.zip') or "
                       "m.endswith('crashreporter-symbols-full.zip')"),
        ('testsUrl', "m.endswith(('tests.tar.bz2', 'tests.zip'))"),
        ('unsignedApkUrl', "m.endswith('apk') and "
                           "'unsigned-unaligned' in m"),
        ('robocopApkUrl', "m.endswith('apk') and 'robocop' in m"),
        ('jsshellUrl', "'jsshell-' in m and m.endswith('.zip')"),
        ('partialMarUrl', "m.endswith('.mar') and '.partial.' in m"),
        ('completeMarUrl', "m.endswith('.mar')"),
    ]

    def __init__(self, **kwargs):
        super(MakeUploadOutputParser, self).__init__(**kwargs)
        self.matches = {}
        self.tbpl_status = TBPL_SUCCESS

    def parse_single_line(self, line):
        prop_assigned = False
        pat = r'''^(https?://.*?\.(?:tar\.bz2|dmg|zip|apk|rpm|mar|tar\.gz))$'''
        m = re.compile(pat).match(line)
        if m:
            m = m.group(1)
            for prop, condition in self.property_conditions:
                if eval(condition):
                    self.matches[prop] = m
                    prop_assigned = True
                    break
            if not prop_assigned:
                # if we found a match but haven't identified the prop then this
                # is the packageURL. Let's consider this the else block
                self.matches['packageUrl'] = m

        # now let's check for retry errors which will give log levels:
        # tbpl status as RETRY and mozharness status as WARNING
        for error_check in self.tbpl_error_list:
            if error_check['regex'].search(line):
                self.num_warnings += 1
                self.warning(line)
                self.tbpl_status = self.worst_level(
                    error_check['level'], self.tbpl_status,
                    levels=TBPL_WORST_LEVEL_TUPLE
                )
                break
        else:
            self.info(line)


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
        'mulet': 'builds/releng_sub_%s_configs/%s_mulet.py',
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


class BuildScript(BuildbotMixin, PurgeMixin, MockMixin, BalrogMixin,
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
                                           self.builduid,
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

    def query_build_env(self, replace_dict=None, **kwargs):
        c = self.config

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

        # first grab the buildid
        env['MOZ_BUILD_DATE'] = self.query_buildid()

        if self.query_is_nightly():
            env["IS_NIGHTLY"] = "yes"
            # in branch_specifics.py we might set update_channel explicitly
            if c.get('update_channel'):
                env["MOZ_UPDATE_CHANNEL"] = c['update_channel']
            else:  # let's just give the generic channel based on branch
                env["MOZ_UPDATE_CHANNEL"] = "nightly-%s" % (self.branch,)

        if self.config.get('pgo_build'):
            env['IS_PGO'] = '1'

        if c.get('enable_signing'):
            moz_sign_cmd = subprocess.list2cmdline(
                self.query_moz_sign_cmd(formats=None)
            )
            # windows fix
            env['MOZ_SIGN_CMD'] = moz_sign_cmd.replace('\\', '\\\\\\\\')

        # we can't make env an attribute of self because env can change on
        # every call for reasons like MOZ_SIGN_CMD
        return env

    def query_build_upload_env(self):
        c = self.config
        upload_env = {}
        if c.get('upload_env'):
            upload_env.update(c['upload_env'])
        if not upload_env.get("UPLOAD_HOST") and c.get('stage_server'):
            upload_env['UPLOAD_HOST'] = c['stage_server']

        # _query_post_upload_cmd returns a list (a cmd list), for env sake here
        # let's make it a string
        pst_up_cmd = ' '.join([str(i) for i in self._query_post_upload_cmd()])
        upload_env['POST_UPLOAD_CMD'] = pst_up_cmd

        return upload_env

    def query_check_test_env(self):
        c = self.config
        dirs = self.query_abs_dirs()
        check_test_env = {}
        if c.get('check_test_env'):
            for env_var, env_value in c['check_test_env'].iteritems():
                check_test_env[env_var] = env_value % dirs
        return check_test_env

    def _query_moz_symbols_buildid(self):
        # this is a bit confusing but every platform that make
        # uploadsymbols may or may not include a
        # MOZ_SYMBOLS_EXTRA_BUILDID in the env and the value of this
        # varies.
        # logic goes:
        #   If it's the release branch, we only include it for
        # 64bit platforms and we use just the platform as value.
        #   If it's a project branch off m-c, we include only the branch
        # for the value on 32 bit platforms and we include both the
        # platform and branch for 64 bit platforms
        c = self.config
        moz_symbols_extra_buildid = ''
        if c.get('use_platform_in_symbols_extra_buildid'):
            moz_symbols_extra_buildid += self.stage_platform
        if c.get('use_branch_in_symbols_extra_buildid'):
            if moz_symbols_extra_buildid:
                moz_symbols_extra_buildid += '-%s' % (self.branch,)
            else:
                moz_symbols_extra_buildid = self.branch
        return moz_symbols_extra_buildid

    def _query_who(self):
        """ looks for who triggered the build with a change.

        This is used for things like try builds where the upload dir is
        associated with who pushed to try. First it will look in self.config
        and failing that, will poll buildbot_config
        If nothing is found, it will default to returning "nobody@example.com"
        """
        _who = ''
        if self.config.get('who'):
            _who = self.config['who']
        if self.buildbot_config and 'sourcestamp' in self.buildbot_config:
            if self.buildbot_config['sourcestamp'].get('who'):
                _who = self.buildbot_config['sourcestamp']['who']
        if not _who:
            _who = "nobody@example.com"
        return _who

    def _query_post_upload_cmd(self):
        # TODO support more from postUploadCmdPrefix()
        # as needed (as we introduce builds that use it)
        # h.m.o/build/buildbotcustom/process/factory.py#l119

        c = self.config
        post_upload_cmd = ["post_upload.py"]
        buildid = self.query_buildid()
        revision = self.query_revision()
        platform = self.stage_platform
        who = self._query_who()
        if c.get('pgo_build'):
            platform += '-pgo'

        if c.get('tinderbox_build_dir'):
            # TODO find out if we should fail here like we are
            if not who and revision:
                self.fatal("post upload failed. --tinderbox-builds-dir could "
                           "not be determined. 'who' and/or 'revision unknown")
            # branches like try will use 'tinderbox_build_dir
            tinderbox_build_dir = c['tinderbox_build_dir'] % {
                'who': who,
                'got_revision': revision
            }
        else:
            # the default
            tinderbox_build_dir = "%s-%s" % (self.branch, platform)

        if who:
            post_upload_cmd.extend(["--who", who])
        if c.get('include_post_upload_builddir'):
            post_upload_cmd.extend(
                ["--builddir", "%s-%s" % (self.branch, platform)]
            )
        post_upload_cmd.extend(["--tinderbox-builds-dir", tinderbox_build_dir])
        post_upload_cmd.extend(["-p", c['stage_product']])
        post_upload_cmd.extend(['-i', buildid])
        post_upload_cmd.extend(['--revision', revision])
        if c.get('to_tinderbox_dated'):
            post_upload_cmd.append('--release-to-tinderbox-dated-builds')
        if c.get('release_to_try_builds'):
            post_upload_cmd.append('--release-to-try-builds')
        if self.query_is_nightly():
            post_upload_cmd.extend(['-b', self.branch])
            post_upload_cmd.append('--release-to-dated')
            if c['platform_supports_post_upload_to_latest']:
                post_upload_cmd.append('--release-to-latest')
        return post_upload_cmd

    def _ccache_z(self):
        """clear ccache stats."""
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        if os.path.exists(dirs['abs_src_dir']):
            self.run_command(command=['ccache', '-z'],
                             cwd=dirs['abs_src_dir'],
                             env=env)

    def _ccache_s(self):
        """print ccache stats. only done for unix like platforms"""
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        cmd = ['ccache', '-s']
        self.run_command(cmd, cwd=dirs['abs_src_dir'], env=env)

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
        # TODO make this method its own action
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

    def _count_ctors(self):
        """count num of ctors and set testresults."""
        dirs = self.query_abs_dirs()
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
        output = output.split("\t")
        num_ctors = int(output[0])
        testresults = [('num_ctors', 'num_ctors', num_ctors, str(num_ctors))]
        self.set_buildbot_property('num_ctors',
                                   num_ctors,
                                   write_to_file=True)
        self.set_buildbot_property('testresults',
                                   testresults,
                                   write_to_file=True)

    def _count_vsize(self):
        """gets linker vsize and sets it to testresults."""
        dirs = self.query_abs_dirs()
        vsize_path = os.path.join(
            dirs['abs_obj_dir'], 'toolkit', 'library', 'linker-vsize'
        )
        cmd = ['cat', vsize_path]
        vsize = int(self.get_output_from_command(cmd, cwd=dirs['abs_src_dir']))
        testresults = [('libxul_link', 'libxul_link', vsize, str(vsize))]
        self.set_buildbot_property('vsize', vsize, write_to_file=True)
        self.set_buildbot_property('testresults',
                                   testresults,
                                   write_to_file=True)

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
        graph_server_path = os.path.join(dirs['abs_tools_dir'],
                                         'lib',
                                         'python')
        # graph server takes all our build properties we had initially
        # (buildbot_config) and what we updated to since
        # the script ran (buildbot_properties)
        # TODO it would be better to grab all the properties that were
        # persisted to file rather than use whats in the buildbot_properties
        # live object so we become less action dependant.
        graph_props_path = os.path.join(c['base_work_dir'],
                                        "graph_props.json")
        all_current_props = dict(
            chain(self.buildbot_config['properties'].items(),
                  self.buildbot_properties.items())
        )
        # graph_server_post.py expects a file with 'properties' key
        graph_props = dict(properties=all_current_props)
        self.dump_config(graph_props_path, graph_props)

        gs_env = self.query_build_env()
        gs_env.update({'PYTHONPATH': graph_server_path})
        resultsname = c['base_name'] % {'branch': self.branch}
        cmd = ['python', graph_server_post_path]
        cmd.extend(['--server', c['graph_server']])
        cmd.extend(['--selector', c['graph_selector']])
        cmd.extend(['--branch', self._query_graph_server_branch_name()])
        cmd.extend(['--buildid', self.query_buildid()])
        cmd.extend(['--sourcestamp',
                    self.query_buildbot_property('sourcestamp')])
        cmd.extend(['--resultsname', resultsname])
        cmd.extend(['--properties-file', graph_props_path])
        cmd.extend(['--timestamp', str(self.epoch_timestamp)])

        self.info("Obtaining graph server post results")
        result_code = self.retry(self.run_command,
                                 args=(cmd,),
                                 kwargs={'cwd': dirs['abs_src_dir'],
                                         'env': gs_env})
        if result_code != 0:
            self.add_summary('Automation Error: failed graph server post',
                             level=ERROR)
            self.worst_buildbot_status = self.worst_level(
                TBPL_EXCEPTION, self.worst_buildbot_status,
                TBPL_STATUS_DICT.keys()
            )

        else:
            self.info("graph server post ok")

    def _query_graph_server_branch_name(self):
        c = self.config
        if c.get('graph_server_branch_name'):
            return c['graph_server_branch_name']
        else:
            # capitalize every word in between '-'
            branch_list = self.branch.split('-')
            branch_list = [elem.capitalize() for elem in branch_list]
            return '-'.join(branch_list)

    def _generate_build_props(self):
        """set buildid, sourcestamp, appVersion, and appName."""
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config',
                                               'printconfigsetting.py')
        if (not os.path.exists(print_conf_setting_path) or
                not os.path.exists(dirs['abs_app_ini_path'])):
            self.error("Can't set the following properties: "
                       "buildid, sourcestamp, appVersion, and appName. "
                       "Required paths missing. Verify both %s and %s "
                       "exist. These paths require the 'build' action to be "
                       "run prior to this" % (print_conf_setting_path,
                                              dirs['abs_app_ini_path']))
        self.info("Setting properties found in: %s" % dirs['abs_app_ini_path'])
        base_cmd = [
            'python', print_conf_setting_path, dirs['abs_app_ini_path'], 'App'
        ]
        properties_needed = [
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
            self.mkdir_p(mozbuild_path)
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
        mach_props = os.path.join(
            self.query_abs_dirs()['abs_obj_dir'], 'mach_build_properties.json'
        )
        if os.path.exists(mach_props):
            self.info("Removing previous mach property file: %s" % mach_props)
            self.rmtree(mach_props)

    def build(self):
        """builds application."""
        env = self.query_build_env()
        env.update(self.query_build_upload_env())
        env.update(self.query_check_test_env())
        symbols_extra_buildid = self._query_moz_symbols_buildid()
        if symbols_extra_buildid:
            env['MOZ_SYMBOLS_EXTRA_BUILDID'] = symbols_extra_buildid

        # XXX HACK DO NOT COMMIT
        dirs = self.query_abs_dirs()
        self.copyfile(os.path.join(dirs['base_work_dir'], 'buildprops.json'),
                      os.path.join(dirs['abs_work_dir'], 'buildprops.json'))

        python = self.query_exe('python2.7')
        return_code = self.run_command_m(
            command=[python, 'mach', 'build'], cwd=self.query_abs_dirs()[
                'abs_src_dir'],
            env=env
        )
        if return_code:
            self.return_code = 2  # failure

    def postflight_build(self, console_output=True):
        """grabs properties set by mach build."""
        mach_properties_path = os.path.join(
            self.query_abs_dirs()['abs_obj_dir'], 'mach_build_properties.json'
        )
        self.info("setting properties set by mach build. Looking in path: %s"
                  % mach_properties_path)
        if os.path.exists(mach_properties_path):
            with open(mach_properties_path) as build_property_file:
                build_props = json.load(build_property_file)
                if console_output:
                    self.info("Properties set from 'mach build'")
                    pprint.pformat(build_props)
            for key, prop in build_props.iteritems():
                self.set_buildbot_property(key, prop, write_to_file=True)
        else:
            self.fatal("Could not find any properties set from mach build. "
                       "Path does not exist: %s" % mach_properties_path)
        # now set the additional properties that mach did not set...
        self._generate_build_props()
        if self.config.get('enable_ccache'):
            self._ccache_s()

    def generate_build_stats(self):
        """grab build stats following a compile.

        This action handles all statitics from a build: 'count_ctors' and
        'vsize' and then posts to graph server the results.
        We only post to graph server for non nightly build
        """
        c = self.config
        # enable_max_vsize will be True for builds like pgo win32 builds
        enable_max_vsize = c.get('enable_max_vsize') and c.get('pgo_build')
        if enable_max_vsize or c.get('enable_count_ctors'):
            if c.get('enable_count_ctors'):
                self.info("counting ctors...")
                self._count_ctors()
                num_ctors = self.buildbot_properties.get('num_ctors', 'unknown')
                self.info("TinderboxPrint: num_ctors: %s" % (num_ctors,))
            if enable_max_vsize:
                self.info("getting vsize...")
                self._count_vsize()
            if not self.query_is_nightly():
                self._graph_server_post()
            else:
                self.info("We are not posting to graph server as this is a "
                          "nightly build.")
        else:
            self.info("Nothing to do for this action since ctors and vsize "
                      "counts are disabled for this build.")

    def sendchanges(self):
        # TODO rip out this logic and put it in build configs
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

        if c.get('enable_talos_sendchange'):
            if c.get('pgo_build'):
                build_type = 'pgo-'
            else:  # we don't do talos sendchange for debug so no need to check
                build_type = ''  # leave 'opt' out of branch for talos
            talos_branch = "%s-%s-%s%s" % (self.branch,
                                           self.stage_platform,
                                           build_type,
                                           'talos')
            self.sendchange(downloadables=[installer_url],
                            branch=talos_branch,
                            username='sendchange',
                            sendchange_props=sendchange_props)

        if c.get('enable_unittest_sendchange'):
            # do unittest sendchange

            # we need a way to make opt builds use pgo branch sendchanges.
            # if the branch supports per_checkin and this platform is in
            # pgo platforms (see branch_specifics.py), use pgo instead of opt.
            override_opt_branch = (self.stage_platform in c['pgo_platforms'] and
                                   c.get('branch_uses_per_checkin_strategy'))
            if c.get('debug_build'):
                build_type = ''  # for debug builds we append nothing
            elif c.get('pgo_build') or override_opt_branch:
                build_type = '-pgo'
            else:  # generic opt build
                build_type = '-opt'

            if c.get('unittest_platform'):
                platform = c['unittest_platform']
            else:
                platform = self.stage_platform

            platform_and_build_type = "%s%s" % (platform, build_type)
            unittest_branch = "%s-%s-%s" % (self.branch,
                                            platform_and_build_type,
                                            'unittest')
            self.sendchange(downloadables=[installer_url, tests_url],
                            branch=unittest_branch,
                            sendchange_props=sendchange_props)

    def update(self):
        """ submit balrog update steps. """
        c = self.config
        if not self.query_is_nightly():
            self.info("Not a nightly build, skipping balrog submission.")
            return

        if not self.config.get("balrog_api_root"):
            self.fatal("balrog_api_root not set; skipping balrog submission.")
            return

        if c['balrog_api_root']:
            self.submit_balrog_updates()

    def _post_fatal(self, message=None, exit_code=None):
        if not self.return_code:  # only overwrite return_code if it's 0
            self.error('setting return code to 2 because fatal was called')
            self.return_code = 2

    @PostScriptRun
    def _summarize(self):
        """ If this is run in automation, ensure the return code is valid and
        set it to one if it's not. Finally, log any summaries we collected
        from the script run.
        """
        if self.config.get("is_automation"):
            # let's ignore all mention of buildbot/tbpl status until this
            # point so it will be easier to manage
            if self.return_code not in AUTOMATION_EXIT_CODES:
                self.error("Return code is set to: %s and is outside of "
                           "automation's known values. Setting to 2(failure). "
                           "Valid return codes %s" % (self.return_code,
                                                      AUTOMATION_EXIT_CODES))
                self.return_code = 2
            for status, return_code in EXIT_STATUS_DICT.iteritems():
                if return_code == self.return_code:
                    self.buildbot_status(status, TBPL_STATUS_DICT[status])
        self.summary()
