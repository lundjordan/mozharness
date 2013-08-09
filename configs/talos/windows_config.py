import os
import socket

PYTHON = 'c:/mozilla-build/python27/python'
PYTHON_DLL = 'c:/mozilla-build/python27/python27.dll'
VENV_PATH = os.path.join(os.getcwd(), 'build/venv')

config = {
    "log_name": "talos",
    "buildbot_json_path": "buildprops.json",
    "installer_path": "installer.exe",
    "virtualenv_path": VENV_PATH,
    "virtualenv_python_dll": PYTHON_DLL,
    "pypi_url": "http://repos/python/packages/",
    "find_links": ["http://repos/python/packages/"],
    "pip_index": False,
    "distribute_url": "http://repos/python/packages/distribute-0.6.26.tar.gz",
    "pip_url": "http://repos/python/packages/pip-0.8.2.tar.gz",
    "use_talos_json": True,
    "pywin32_url": "http://repos/python/packages/pywin32-216.win32-py2.7.exe",
    "virtualenv_modules": ['pywin32', 'talos', 'mozinstall'],
    "exes": {
        'python': PYTHON,
        'virtualenv': [PYTHON, 'c:/mozilla-build/buildbotve/virtualenv.py'],
        'easy_install': ['%s/scripts/python' % VENV_PATH,
                         '%s/scripts/easy_install-2.7-script.py' % VENV_PATH],
        'mozinstall': ['%s/scripts/python' % VENV_PATH,
                       '%s/scripts/mozinstall-script.py' % VENV_PATH],
        'hg': 'c:/mozilla-build/hg/hg',
    },
    "title": socket.gethostname().split('.')[0],
    "results_url": "http://graphs.mozilla.org/server/collect.cgi",
    "datazilla_urls": ["https://datazilla.mozilla.org/talos"],
    # "datazilla_authfile": os.path.join(os.getcwd(), "oauth.txt"),
    "default_actions": [
        "clobber",
        "read-buildbot-config",
        "download-and-extract",
        "clone-talos",
        "create-virtualenv",
        "install",
        "run-tests",
    ],
    "python_webserver": False,
    "webroot": 'c:/slave/talos-data',
    "populate_webroot": True,
    # Srsly gly? Ys
    "webroot_extract_cmd": r'''c:/mozilla-build/msys/bin/bash -c "PATH=/c/mozilla-build/msys/bin:$PATH tar zx --strip-components=1 -f '%(tarball)s' --wildcards '**/talos/'"''',
    # "metro-immersive": False,
    "metro_harness_dir": "mozbase/mozrunner/mozrunner/resources",
    "metro_test_harness_exe": "metrotestharness.exe",
    # just needed until we update m-c talos.json
    "talos_json_url": "http://hg.mozilla.org/users/jlund_mozilla.com/talos-json/raw-file/b374e24e2e6f/talos.json"
    # "talos_json": {
    #                 "talos.zip": {
    #                     "url": "http://build.mozilla.org/talos/zips/talos.fcbb9d7d3c78.zip",
    #                     "path": ""
    #                 },
    #                 "global": {
    #                     "talos_repo": "http://hg.mozilla.org/build/talos",
    #                     "talos_revision": "4063ef2a221e"
    #                 },
    #                 "suites": {
    #                     "chromez": {
    #                         "tests": ["tresize"],
    #                         "talos_options": [
    #                             "--mozAfterPaint",
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median"
    #                         ]
    #                     },
    #                     "dirtypaint": {
    #                         "tests": [
    #                             "tspaint_places_generated_med",
    #                             "tspaint_places_generated_max"
    #                         ],
    #                         "talos_addons": [
    #                             "http://build.mozilla.org/talos/profiles/dirtyDBs.zip",
    #                             "http://build.mozilla.org/talos/profiles/dirtyMaxDBs.zip"
    #                         ],
    #                         "talos_options": [
    #                             "--setPref",
    #                             "hangmonitor.timeout=0",
    #                             "--mozAfterPaint"
    #                         ]
    #                     },
    #                     "dromaeojs-metro": {
    #                         "tests": [
    #                             "dromaeo_css",
    #                             "dromaeo_dom",
    #                             "kraken:v8_7"
    #                         ]
    #                     },
    #                     "dromaeojs": {
    #                         "tests": [
    #                             "dromaeo_css",
    #                             "dromaeo_dom",
    #                             "kraken:v8_7"
    #                         ]
    #                     },
    #                     "other": {
    #                         "tests": ["tscrollr", "a11yr", "ts_paint", "tpaint"],
    #                         "talos_options": [
    #                             "--mozAfterPaint",
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median"
    #                         ]
    #                     },
    #                     "svgr": {
    #                         "tests": ["tsvgr", "tsvgr_opacity"],
    #                         "talos_options": [
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median"
    #                         ]
    #                     },
    #                     "rafx": {
    #                         "tests": ["tscrollx", "tsvgx", "tcanvasmark"],
    #                         "talos_options": [
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median"
    #                         ]
    #                     },
    #                     "tpn": {
    #                         "tests": ["tp5n"],
    #                         "pagesets_url": "http://build.mozilla.org/talos/zips/tp5n.zip",
    #                         "pagesets_parent_dir_path": "talos/page_load_test/",
    #                         "pagesets_manifest_path": "talos/page_load_test/tp5n/tp5n.manifest",
    #                         "plugins": {
    #                             "32": "http://build.mozilla.org/talos/zips/flash32_10_3_183_5.zip",
    #                             "64": "http://build.mozilla.org/talos/zips/flash64_11_0_d1_98.zip"
    #                         },
    #                         "talos_options": [
    #                             "--mozAfterPaint",
    #                             "--responsiveness",
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median",
    #                             "--test_timeout",
    #                             "3600"
    #                         ]
    #                     },
    #                     "tp5o": {
    #                         "tests": ["tp5o"],
    #                         "pagesets_url": "http://build.mozilla.org/talos/zips/tp5n.zip",
    #                         "pagesets_parent_dir_path": "talos/page_load_test/",
    #                         "pagesets_manifest_path": "talos/page_load_test/tp5n/tp5o.manifest",
    #                         "plugins": {
    #                             "32": "http://build.mozilla.org/talos/zips/flash32_10_3_183_5.zip",
    #                             "64": "http://build.mozilla.org/talos/zips/flash64_11_0_d1_98.zip"
    #                         },
    #                         "talos_options": [
    #                             "--mozAfterPaint",
    #                             "--responsiveness",
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median",
    #                             "--test_timeout",
    #                             "3600"
    #                         ]
    #                     },
    #                     "xperf": {
    #                         "tests": ["tp5n"],
    #                         "pagesets_url": "http://build.mozilla.org/talos/zips/tp5n.zip",
    #                         "pagesets_parent_dir_path": "talos/page_load_test/",
    #                         "pagesets_manifest_path": "talos/page_load_test/tp5n/tp5n.manifest",
    #                         "plugins": {
    #                             "32": "http://build.mozilla.org/talos/zips/flash32_10_3_183_5.zip",
    #                             "64": "http://build.mozilla.org/talos/zips/flash64_11_0_d1_98.zip"
    #                         },
    #                         "talos_options": [
    #                             "--mozAfterPaint",
    #                             "--xperf_path",
    #                             "\"c:/Program Files/Microsoft Windows Performance Toolkit/xperf.exe\"",
    #                             "--filter",
    #                             "ignore_first:5",
    #                             "--filter",
    #                             "median",
    #                             "C:/slave/talos-data/talos/xperf.config"
    #                         ]
    #                     }
    #                 }
    #             }


}
