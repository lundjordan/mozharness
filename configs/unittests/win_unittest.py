#### OS Specifics ####
APP_NAME_DIR = "firefox"
BINARY_PATH = "firefox.exe"
INSTALLER_PATH = "installer.tar.bz2"
XPCSHELL_NAME = 'xpcshell.exe'
ADJUST_SCREEN_RESOLUTION = False
DISABLE_SCREEN_SAVER = False
#####

config = {

        "app_name_dir" : APP_NAME_DIR,
        "installer_path" : INSTALLER_PATH,
        "binary_path" : APP_NAME_DIR + "/" + BINARY_PATH,

        # TODO find out if I need simple_json_url
        "buildbot_json_path": "buildprops.json",
        "simplejson_url": "http://build.mozilla.org/talos/zips/simplejson-2.2.1.tar.gz",

        "repos": [{
            "repo": "http://hg.mozilla.org/build/tools",
            "revision": "default",
            "dest": "tools"
        }],


        #global unittest options
        "global_test_options" : 
        {
            "app_name" : "--appname={binary_path}",
            "util_path" : "--utility-path=tests/bin",
            "extra_prof_path" : "--extra-profile-file=tests/bin/plugins",
            "symbols_path" : "--symbols-path={symbols_path}"
        },

        "run_file_names" : {
            "mochitest" : "runtests.py",
            "reftest" : "runreftest.py",
            "xpcshell" : "runxpcshelltests.py"
        },

        #global mochitest options
        "global_mochitest_options" : [
            "--certificate-path=tests/certs", "--autorun",
            "--close-when-done", "--console-level=INFO",
        ],


        #local mochi suites
        "all_mochitest_suites" :
        {
            "plain1" : ["--total-chunks=5", "--this-chunk=1", "--chunk-by-dir=4"],
            "plain2" : ["--total-chunks=5", "--this-chunk=2", "--chunk-by-dir=4"],
            "plain3" : ["--total-chunks=5", "--this-chunk=3", "--chunk-by-dir=4"],
            "plain4" : ["--total-chunks=5", "--this-chunk=4", "--chunk-by-dir=4"],
            "plain5" : ["--total-chunks=5", "--this-chunk=5", "--chunk-by-dir=4"],
            "chrome" : ["--chrome"],
            "browser-chrome" : ["--browser-chrome"],
            "a11y" : ["--a11y"],
            "plugins" : ["--setpref='dom.ipc.plugins.enabled=false'",
                "--test-path='modules/plugin/test'"]
        },

        #local reftests suites
        "all_reftest_suites" :
        {
            "reftest" : ["tests/reftest/tests/layout/reftests/reftest.list"],
            "crashtest" : ["tests/reftest/tests/layout/reftests/crashtests.list"],
            "jsreftest" : ["--extra-profile-file=tests/jsreftest/tests/user.js", "tests/jsreftests/jstests.list"],
        },

        "xpcshell_name" : XPCSHELL_NAME,

        "all_xpcshell_suites" : {
            "xpcshell" : ["--manifest=tests/xpcshell/tests/all-test-dirs.list",
                    "application/firefox/" + XPCSHELL_NAME]
        },

        "preflight_run_cmd_suites" : [
                {
                    "name" : "disable_screen_saver",
                    "cmd" : ["xset", "s", "reset"],
                    "enabled" : DISABLE_SCREEN_SAVER
                },
                {
                    "name" : "adjust_screen_resolution",
                    "cmd" : [
                        "bash", "-c", "screenresolution", "get", "&&", "screenresolution",
                        "list", "&&", "system_profiler", "SPDisplaysDataType"
                    ],
                    "enabled" : ADJUST_SCREEN_RESOLUTION
                },
        ],

}
