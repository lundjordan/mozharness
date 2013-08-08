#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""
run talos tests in a virtualenv
"""

import os
import pprint
import re

from mozharness.base.config import parse_config_file
from mozharness.base.errors import PythonErrorList
from mozharness.base.log import OutputParser, DEBUG, ERROR, CRITICAL, FATAL
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options, INSTALLER_SUFFIXES
from mozharness.base.vcs.vcsbase import MercurialScript

TalosErrorList = PythonErrorList + [
 {'regex': re.compile(r'''run-as: Package '.*' is unknown'''), 'level': DEBUG},
 {'substr': r'''FAIL: Graph server unreachable''', 'level': CRITICAL},
 {'substr': r'''FAIL: Busted:''', 'level': CRITICAL},
 {'substr': r'''FAIL: failed to cleanup''', 'level': ERROR},
 {'substr': r'''erfConfigurator.py: Unknown error''', 'level': CRITICAL},
 {'substr': r'''talosError''', 'level': CRITICAL},
 {'regex': re.compile(r'''No machine_name called '.*' can be found'''), 'level': CRITICAL},
 {'substr': r"""No such file or directory: 'browser_output.txt'""",
  'level': CRITICAL,
  'explanation': r"""Most likely the browser failed to launch, or the test was otherwise unsuccessful in even starting."""},
]

# TODO: check for running processes on script invocation

class TalosOutputParser(OutputParser):
    minidump_regex = re.compile(r'''talosError: "error executing: '(\S+) (\S+) (\S+)'"''')
    minidump_output = None
    def parse_single_line(self, line):
        """ In Talos land, every line that starts with RETURN: needs to be
        printed with a TinderboxPrint:"""
        if line.startswith("RETURN:"):
            line.replace("RETURN:", "TinderboxPrint:")
        m = self.minidump_regex.search(line)
        if m:
            self.minidump_output = (m.group(1), m.group(2), m.group(3))
        super(TalosOutputParser, self).parse_single_line(line)


talos_config_options = [
    [["-a", "--tests"],
     {'action': 'extend',
      "dest": "tests",
      "default": [],
      "help": "Specify the tests to run"
      }],
    [["--results-url"],
     {'action': 'store',
      'dest': 'results_url',
      'default': None,
      'help': "URL to send results to"
      }],
    ]


class Talos(TestingMixin, MercurialScript):
    """
    install and run Talos tests:
    https://wiki.mozilla.org/Buildbot/Talos
    """

    config_options = [
        [["--talos-url"],
         {"action": "store",
          "dest": "talos_url",
          "default": "http://hg.mozilla.org/build/talos/archive/tip.tar.gz",
          "help": "Specify the talos package url"
          }],
        [["--use-talos-json"],
          {"action": "store_true",
           "dest": "use_talos_json",
           "default": False,
           "help": "Use talos config from talos.json"
           }],
        [["--suite"],
          {"action": "store",
           "dest": "suite",
           "help": "Talos suite to run (from talos json)"
           }],
        [["--branch-name"],
          {"action": "store",
           "dest": "branch",
           "help": "Graphserver branch to report to"
           }],
        # [["--metro-immersive"],
        #   {"action": "store_true",
        #    "dest": "metro_immersive",
        #    "help": "Tells windows 8 machines to run tests with Metro Browser"
        #    }],
        [["--system-bits"],
          {"action": "store",
           "dest": "system_bits",
           "type": "choice",
           "default": "32",
           "choices": ['32', '64'],
           "help": "Testing 32 or 64 (for talos json plugins)"
           }],
        [["--add-option"],
          {"action": "extend",
           "dest": "talos_extra_options",
           "default": None,
           "help": "extra options to talos"
           }],
        ] + talos_config_options + testing_config_options

    def __init__(self, **kwargs):
        kwargs.setdefault('config_options', self.config_options)
        kwargs.setdefault('all_actions', ['clobber',
                                          'read-buildbot-config',
                                          'download-and-extract',
                                          'clone-talos',
                                          'create-virtualenv',
                                          'install',
                                          'run-tests',
                                         ])
        kwargs.setdefault('default_actions', ['clobber',
                                              'download-and-extract',
                                              'clone-talos',
                                              'create-virtualenv',
                                              'install',
                                              'run-tests',
                                             ])
        kwargs.setdefault('config', {})
        kwargs['config'].setdefault('virtualenv_modules', ["talos", "mozinstall"])
        super(Talos, self).__init__(**kwargs)

        self.workdir = self.query_abs_dirs()['abs_work_dir'] # convenience

        # results output
        if self.config.get('suite').endswith('-metro'):
            # TEMPORARY CODE: this script takes a `suite` option that is used as a
            # key from a talos_json_url
            # (eg: http://hg.mozilla.org/mozilla-central/raw-file/s(revision)/testing/talos/talos.json)
            # if we pass a suite with a '-metro' suffix through buildbot or a developer,
            # the talos.json file in m-c won't know about it yet.
            # Until we modify that json file in m-c to add win metro based keys/values,
            # let's just capture the fact we want 'metro_immersive' then use the
            # non metro equivalent from the talos.json file
            # (eg: self.talos_json_config['suites']['dromaeojs'])
            # self.config['suite'] = self.config['suite'].replace('-metro', '')
            self.config['metro_immersive'] = True
            self.info('running metro mode' + str(self.config('suite')))
        self.results_url = self.config.get('results_url')
        if self.results_url is None:
            # use a results_url by default based on the class name in the working directory
            self.results_url = 'file://%s' % os.path.join(self.workdir, self.__class__.__name__.lower() + '.txt')
        self.installer_url = self.config.get("installer_url")
        self.test_url = self.config.get('test_url')
        self.talos_json_url = self.config.get("talos_json_url")
        self.talos_json = self.config.get("talos_json")
        self.talos_json_config = self.config.get("talos_json_config")
        self.talos_path = os.path.join(self.workdir, 'talos_repo')
        self.has_cloned_talos = False
        self.tests = None
        self.pagesets_url = None
        self.pagesets_parent_dir_path = None
        self.pagesets_manifest_path = None
        self.abs_pagesets_paths = None
        self.pagesets_manifest_filename = None
        self.pagesets_manifest_parent_path = None
        if 'run-tests' in self.actions:
            self.preflight_run_tests()



    def query_abs_dirs(self):
        c = self.config
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(Talos, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                                            'tests')
        dirs['abs_metro_harness_dir'] = os.path.join(dirs['abs_test_dir'],
                                                     c.get('metro_harness_dir', ''))
        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_talos_json_url(self):
        """Hacky, but I haven't figured out a better way to get the
        talos json url before we install the build.

        We can't get this information after we install the build, because
        we have to create the virtualenv to use mozinstall, and talos_url
        is specified in the talos json.
        """
        if self.talos_json_url:
            return self.talos_json_url
        self.info("Guessing talos json url...")
        if not self.installer_url:
            self.read_buildbot_config()
            self.postflight_read_buildbot_config()
            if not self.installer_url:
                self.fatal("Can't figure out talos_json_url without an installer_url!")
        for suffix in INSTALLER_SUFFIXES:
            if self.installer_url.endswith(suffix):
                build_txt_url = self.installer_url[:-len(suffix)] + '.txt'
                break
        else:
            self.fatal("Can't figure out talos_json_url from installer_url %s!" % self.installer_url)
        build_txt_file = self.download_file(build_txt_url, parent_dir=self.workdir)
        if not build_txt_file:
            self.fatal("Can't download %s to guess talos_json_url!" % build_txt_url)
        # HG hardcode?
        revision_re = re.compile(r'''([a-zA-Z]+://.+)/rev/([0-9a-fA-F]{10})''')
        contents = self.read_from_file(build_txt_file, error_level=FATAL).splitlines()
        for line in contents:
            m = revision_re.match(line)
            if m:
                break
        else:
            self.fatal("Can't figure out talos_json_url from %s!" % build_txt_file)
        self.talos_json_url = "%s/raw-file/%s/testing/talos/talos.json" % (m.group(1), m.group(2))
        return self.talos_json_url

    def download_talos_json(self):
        talos_json_url = self.query_talos_json_url()
        self.talos_json = self.download_file(talos_json_url,
                                             parent_dir=self.workdir,
                                             error_level=FATAL)

    def query_talos_json_config(self):
        """Return the talos json config; download and read from the
        talos_json_url if need be."""
        if self.talos_json_config:
            return self.talos_json_config
        c = self.config
        if not c['use_talos_json']:
            return
        if not c['suite']:
            self.fatal("To use talos_json, you must define use_talos_json, suite.")
            return
        if not self.talos_json:
            talos_json_url = self.query_talos_json_url()
            if not talos_json_url:
                self.fatal("Can't download talos_json without a talos_json_url!")
            self.download_talos_json()
            self.info('made it here' + str(talos_json_url))
        self.info('self.talos_json' + str(self.talos_json))
        self.talos_json_config = parse_config_file(self.talos_json)
        self.info(pprint.pformat(self.talos_json_config))
        return self.talos_json_config

    def query_tests(self):
        """Determine if we have tests to run.

        Currently talos json will take precedence over config and command
        line options; if that's not a good default we can switch the order.
        """
        if self.tests is not None:
            return self.tests
        c = self.config
        if c['use_talos_json']:
            if not c['suite']:
                self.fatal("Can't use_talos_json without a --suite!")
            talos_config = self.query_talos_json_config()
            try:
                self.tests = talos_config['suites'][c['suite']]['tests']
            except KeyError, e:
                self.error("Badly formed talos_json for suite %s; KeyError trying to access talos_config['suites'][%s]['tests']: %s" % (c['suite'], c['suite'], str(e)))
        elif c['tests']:
            self.tests = c['tests']
        # Ignore these tests, specifically so we can not run a11yr on osx
        if c.get('ignore_tests'):
            for test in c['ignore_tests']:
                if test in self.tests:
                    del self.tests[self.tests.index(test)]
        return self.tests

    def query_talos_options(self):
        options = []
        c = self.config
        if self.query_talos_json_config():
            options += self.talos_json_config['suites'][c['suite']].get('talos_options', [])
        if c.get('talos_extra_options'):
            options += c['talos_extra_options']
        return options

    def query_talos_repo(self):
        """Where do we install the talos python package from?
        This needs to be overrideable by the talos json.
        """
        default_repo = "http://hg.mozilla.org/build/talos"
        if self.query_talos_json_config():
            return self.talos_json_config.get('global', {}).get('talos_repo', default_repo)
        else:
            return self.config.get('talos_repo', default_repo)

    def query_talos_revision(self):
        """Which talos revision do we want to use?
        This needs to be overrideable by the talos json.
        """
        if self.query_talos_json_config():
            return self.talos_json_config['global']['talos_revision']
        else:
            return self.config.get('talos_revision')

    def query_pagesets_url(self):
        """Certain suites require external pagesets to be downloaded and
        extracted.
        """
        if self.pagesets_url:
            return self.pagesets_url
        if self.query_talos_json_config():
            self.pagesets_url = self.talos_json_config['suites'][self.config['suite']].get('pagesets_url')
            return self.pagesets_url

    def query_pagesets_parent_dir_path(self):
        """ We have to copy the pageset into the webroot separately.

        Helper method to avoid hardcodes.
        """
        if self.pagesets_parent_dir_path:
            return self.pagesets_parent_dir_path
        if self.query_talos_json_config():
            self.pagesets_parent_dir_path = self.talos_json_config['suites'][self.config['suite']].get('pagesets_parent_dir_path')
            return self.pagesets_parent_dir_path

    def query_pagesets_manifest_path(self):
        """ We have to copy the tp manifest from webroot to talos root when
        those two directories aren't the same, until bug 795172 is fixed.

        Helper method to avoid hardcodes.
        """
        if self.pagesets_manifest_path:
            return self.pagesets_manifest_path
        if self.query_talos_json_config():
            self.pagesets_manifest_path = self.talos_json_config['suites'][self.config['suite']].get('pagesets_manifest_path')
            return self.pagesets_manifest_path

    def query_pagesets_manifest_filename(self):
        if self.pagesets_manifest_filename:
            return self.pagesets_manifest_filename
        else:
            manifest_path = self.query_pagesets_manifest_path()
            self.pagesets_manifest_filename = os.path.basename(manifest_path)
            return self.pagesets_manifest_filename

    def query_pagesets_manifest_parent_path(self):
        if self.pagesets_manifest_parent_path:
            return self.pagesets_manifest_parent_path
        if self.query_talos_json_config():
            manifest_path = self.query_pagesets_manifest_path()
            self.pagesets_manifest_parent_path = os.path.dirname(manifest_path)
            return self.pagesets_manifest_parent_path

    def query_abs_pagesets_paths(self):
        """ Returns a bunch of absolute pagesets directory paths.
        We need this to make the dir and copy the manifest to the local dir.
        """
        if self.abs_pagesets_paths:
            return self.abs_pagesets_paths
        else:
            paths = {}
            manifest_parent_path = self.query_pagesets_manifest_parent_path()
            paths['pagesets_manifest_parent'] = os.path.join(self.talos_path, manifest_parent_path)

            manifest_path = self.query_pagesets_manifest_path()
            paths['pagesets_manifest'] = os.path.join(self.talos_path, manifest_path)

            self.abs_pagesets_paths = paths
            return self.abs_pagesets_paths

    def talos_options(self, args=None, **kw):
        """return options to talos"""
        # binary path
        binary_path = self.binary_path or self.config.get('binary_path')
        if not binary_path:
            self.fatal("Talos requires a path to the binary.  You can specify binary_path or add download-and-extract to your action list.")

        # talos options
        options = ['-v',] # hardcoded options (for now)
        if self.config.get('python_webserver', True):
            options.append('--develop')
        # talos can't gather data if the process name ends with '.exe'
        if binary_path.endswith('.exe'):
            binary_path = binary_path[:-4]
        kw_options = {'output': 'talos.yml', # options overwritten from **kw
                      'executablePath': binary_path,
                      'results_url': self.results_url}
        kw_options['activeTests'] = self.query_tests()
        if self.config.get('title'):
            kw_options['title'] = self.config['title']
        if self.config.get('branch'):
            kw_options['branchName'] = self.config['branch']
        if self.symbols_path:
            kw_options['symbolsPath'] = self.symbols_path
        kw_options.update(kw)
        # talos expects tests to be in the format (e.g.) 'ts:tp5:tsvg'
        tests = kw_options.get('activeTests')
        if tests and not isinstance(tests, basestring):
            tests = ':'.join(tests) # Talos expects this format
            kw_options['activeTests'] = tests
        for key, value in kw_options.items():
            options.extend(['--%s' % key, value])
        # add datazilla results urls
        for url in self.config.get('datazilla_urls', []):
            options.extend(['--datazilla-url', url])
        # add datazilla authfile
        authfile = self.config.get('datazilla_authfile')
        if authfile:
            options.extend(['--authfile', authfile])
        # extra arguments
        if args is None:
            args = self.query_talos_options()
        options += args

        return options

    def talos_conf_path(self, conf):
        """return the full path for a talos .yml configuration file"""
        if os.path.isabs(conf):
            return conf
        return os.path.join(self.workdir, conf)

    def _populate_webroot(self):
        """Populate the production test slaves' webroots"""
        c = self.config
        talos_repo = self.query_talos_repo()
        talos_revision = self.query_talos_revision()
        if not c.get('webroot') or not talos_repo:
            self.fatal("Both webroot and talos_repo need to be set to populate_webroot!")
        self.info("Populating webroot %s..." % c['webroot'])
        talos_webdir = os.path.join(c['webroot'], 'talos')
        self.mkdir_p(c['webroot'], error_level=FATAL)
        self.rmtree(talos_webdir, error_level=FATAL)

        # clone talos' repo
        repo = {
            'repo': talos_repo,
            'vcs': 'hg',
            'dest': self.talos_path,
            'revision': talos_revision
            }
        self.vcs_checkout(**repo)
        self.has_cloned_talos = True

        # the apache server needs the talos directory (talos/talos)
        # to be in the webroot
        src_talos_webdir = os.path.join(self.talos_path, 'talos')
        self.copytree(src_talos_webdir, talos_webdir)

        if c.get('use_talos_json'):
            if self.query_pagesets_url():
                self.info("Downloading pageset...")
                pagesets_path = os.path.join(c['webroot'], self.query_pagesets_parent_dir_path())
                self._download_unzip(self.pagesets_url, pagesets_path)

                # mkdir for the missing manifest directory in talos_repo/talos/page_load_test directory
                abs_pagesets_paths = self.query_abs_pagesets_paths()
                abs_manifest_parent_path = abs_pagesets_paths['pagesets_manifest_parent']
                self.mkdir_p(abs_manifest_parent_path, error_level=FATAL)

                # copy all the manifest file from unzipped zip file into the manifest dir
                src_manifest_file = os.path.join(c['webroot'], self.query_pagesets_manifest_path())
                dest_manifest_file = abs_pagesets_paths['pagesets_manifest']
                self.copyfile(src_manifest_file, dest_manifest_file, error_level=FATAL)
            plugins_url = self.talos_json_config['suites'][c['suite']].get('plugins', {}).get(c['system_bits'])
            if plugins_url:
                self.info("Downloading plugin...")
                # TODO add this path to talos.json ?
                self._download_unzip(plugins_url, os.path.join(talos_webdir, 'base_profile'))
            addons_urls = self.talos_json_config['suites'][c['suite']].get('talos_addons')
            if addons_urls:
                self.info("Downloading addons...")
                for addons_url in addons_urls:
                    self._download_unzip(addons_url, talos_webdir)


    # Action methods. {{{1
    # clobber defined in BaseScript
    # read_buildbot_config defined in BuildbotMixin
    # download_and_extract defined in TestingMixin

    def clone_talos(self):
        c = self.config
        if not c.get('python_webserver', True) and c.get('populate_webroot'):
            self._populate_webroot()

    def create_virtualenv(self, **kwargs):
        """VirtualenvMixin.create_virtualenv() assuemes we're using
        self.config['virtualenv_modules']. Since we are installing
        talos from its source, we have to wrap that method here."""
        # XXX This method could likely be replaced with a PreScriptAction hook.
        if self.has_cloned_talos:
            virtualenv_modules = self.config.get('virtualenv_modules', [])[:]
            if 'talos' in virtualenv_modules:
                i = virtualenv_modules.index('talos')
                virtualenv_modules[i] = {'talos': self.talos_path}
                self.info(pprint.pformat(virtualenv_modules))
            return super(Talos, self).create_virtualenv(modules=virtualenv_modules)
        else:
            return super(Talos, self).create_virtualenv(**kwargs)

    def postflight_create_virtualenv(self):
        """ This belongs in download_and_install() but requires the
        virtualenv to be set up :(

        The real fix here may be a --tpmanifest option for PerfConfigurator.
        """
        c = self.config
        if not c.get('python_webserver', True) and c.get('populate_webroot') \
          and self.query_pagesets_url():
            pagesets_path = self.query_pagesets_manifest_path()
            manifest_source = os.path.join(c['webroot'], pagesets_path)
            manifest_target = os.path.join(self.query_python_site_packages_path(), pagesets_path)
            self.mkdir_p(os.path.dirname(manifest_target))
            self.copyfile(manifest_source, manifest_target)

    def install(self):
        """decorates TestingMixin.install() to handle win metro browser"""
        c = self.config
        dirs = self.query_abs_dirs()
        self.info('made it to talos install()')
        super(Talos, self).install()
        if c.get('metro_immersive'):
            self.info("Triggering Metro Browser Immersive Mode")
            # overwrite self.binary_path set from TestingMixin.install()
            abs_app_dir = os.path.split(self.binary_path)[0]
            orig_metro_path = os.path.join(dirs['abs_metro_harness_dir'],
                                           c.get('metro_test_harness_exe'))
            new_metro_path = os.path.join(abs_app_dir,
                                          c.get('metro_test_harness_exe'))
            self.copyfile(orig_metro_path, new_metro_path)
            if not os.path.exists(self.binary_path):
                self.fatal("metrotestharness executable could not be found")
            self.binary_path = new_metro_path

    def preflight_run_tests(self):
        if not self.query_tests():
            self.fatal("No tests specified; please specify --tests")

    def run_tests(self, args=None, **kw):
        """run Talos tests"""

        # get talos options
        options = self.talos_options(args=args, **kw)

        # XXX temporary python version check
        python = self.query_python_path()
        self.run_command([python, "--version"])
        # run talos tests
        talos = self.query_python_path('talos')
        command = [talos, '--noisy', '--debug'] + options
        parser = TalosOutputParser(config=self.config, log_obj=self.log_obj,
                                   error_list=TalosErrorList)
        self.return_code = self.run_command(command, cwd=self.workdir,
                                            output_parser=parser)
        if parser.minidump_output:
            self.info("Looking at the minidump files for debugging purposes...")
            for item in parser.minidump_output:
                self.run_command(["ls", "-l", item])
