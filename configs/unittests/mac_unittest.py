#### OS Specifics ####
APP_NAME_DIR = "FirefoxNightly.app/Contents/MacOS"
BINARY_PATH = "firefox-bin"
INSTALLER_PATH = "installer.dmg"
XPCSHELL_NAME = 'xpcshell'
DISABLE_SCREEN_SAVER = False
ADJUST_MOUSE_AND_SCREEN = False
#####
config = {
    "app_name_dir" : APP_NAME_DIR,
    "installer_path" : INSTALLER_PATH,
    "binary_path" : APP_NAME_DIR + "/" + BINARY_PATH,
    "xpcshell_name" : XPCSHELL_NAME,
    # TODO find out if I need simple_json_url
    "buildbot_json_path": "buildprops.json",
    "simplejson_url": "http://build.mozilla.org/talos/zips/simplejson-2.2.1.tar.gz",
    "repos": [{
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools"
    }],
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },
    "run_file_names" : {
        "mochitest" : "runtests.py",
        "reftest" : "runreftest.py",
        "xpcshell" : "runxpcshelltests.py"
    },
    "minimum_tests_zip_dirs" : ["bin/*", "certs/*", "modules/*", "mozbase/*"],
    "specific_tests_zip_dirs" : {
        "mochitest" : ["mochitest/*"],
        "reftest" : ["reftest/*", "jsreftest/*"],
        "xpcshell" : ["xpcshell/*"]
        },
    "reftest_options" : [
        "--appname=%(binary_path)s", "--utility-path=tests/bin",
        "--extra-profile-file=tests/bin/plugins","--symbols-path=%(symbols_path)s"
    ],
    "mochitest_options" : [
        "--appname=%(binary_path)s", "--utility-path=tests/bin",
        "--extra-profile-file=tests/bin/plugins","--symbols-path=%(symbols_path)s",
        "--certificate-path=tests/certs", "--autorun", "--close-when-done",
        "--console-level=INFO"
    ],
    "xpcshell_options" : [
        "--symbols-path=%(symbols_path)s"
    ],
    #local mochi suites
    "all_mochitest_suites" : {
        "plain1" : ["--total-chunks=5", "--this-chunk=1", "--chunk-by-dir=4"],
        "plain2" : ["--total-chunks=5", "--this-chunk=2", "--chunk-by-dir=4"],
        "plain3" : ["--total-chunks=5", "--this-chunk=3", "--chunk-by-dir=4"],
        "plain4" : ["--total-chunks=5", "--this-chunk=4", "--chunk-by-dir=4"],
        "plain5" : ["--total-chunks=5", "--this-chunk=5", "--chunk-by-dir=4"],
        "chrome" : ["--chrome"],
        "browser-chrome" : ["--browser-chrome"],
        "plugins" : ['--setpref=dom.ipc.plugins.enabled=false',
                '--setpref=dom.ipc.plugins.enabled.x86_64=false',
                '--ipcplugins']
    },
    #local reftests suites
    "all_reftest_suites" : {
        "reftest" : ["tests/reftest/tests/layout/reftests/reftest.list"],
        "crashtest" : ["tests/reftest/tests/layout/reftests/crashtests.list"],
        "jsreftest" : ["--extra-profile-file=tests/jsreftest/tests/user.js", "tests/jsreftests/jstests.list"],
    },
    "all_xpcshell_suites" : {
        "xpcshell" : ["--manifest=tests/xpcshell/tests/all-test-dirs.list",
            "application/" + APP_NAME_DIR + "/" + XPCSHELL_NAME]
    },
    "preflight_run_cmd_suites" : [
        {
            "name" : "disable_screen_saver",
            "cmd" : ["xset", "s", "reset"],
            "architectures" : ["32bit", "64bit"],
            "halt_on_failure" : False,
            "enabled" : DISABLE_SCREEN_SAVER
        },
        {
            #TODO add error list to this (global errors from buildbot)
            "name" : "run mouse & screen adjustment script",
            "cmd" : [
                # when configs are consolidated this python path will only show
                # for windows.
                "C:\\mozilla-build\\python25\\python.exe",
                "tools/scripts/support/mouse_and_screen_resolution.py",
                "--configuration-url",
                "http://hg.mozilla.org/mozilla-central/raw/tip/" + \
                        "testing/machine-configuration.json"],
            "architectures" : ["32bit"],
            "halt_on_failure" : True,
            "enabled" : ADJUST_MOUSE_AND_SCREEN
        },
    ],
}
