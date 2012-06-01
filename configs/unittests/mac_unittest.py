#### OS Specifics ####
XPCSHELL_NAME = 'xpcshell'
ADJUST_SCREEN_RESOLUTION = True
DISABLE_SCREEN_SAVER = False
#####

config = {

        ###### paths/urls can be implemented on command line as well
        "installer_url" : None, # eg: "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/
                                                # mozilla-central-win32/1334941863/firefox-14.0a1.en-US.win32.zip"

        "tests_url" :  None, # eg "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/
                                        # mozilla-central-win32/1334941863/firefox-14.0a1.en-US.win32.tests.zip"

        "installer_path" : None, # eg "/path/with/something/like/build/application"
        "binary_path" : None, # eg "/path/with/something/like/build/application/firefox/firefox-bin"
        "tests_path" :  None, # eg "/path/with/something/like/build/tests"
        #######


        "symbols_url" : None, # eg: "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/
                                        # mozilla-central-win32/1334941863/firefox-14.0a1.en-US.crashreporter-symbols.zip"

        "repos": [{
            "repo": "http://hg.mozilla.org/build/tools",
            "revision": "default",
            "dest": "tools"
        }],


        #global unittest options
        "global_test_options" : {
            "app_name" : "--appname={binary_path}",
            "util_path" : "--utility-path=tests/bin",
            "extra_prof_path" : "--extra-profile-file=tests/bin/plugins",
            "symbols_path" : "--symbols-path={symbols_path}"
        },

        #global mochitest options
        "global_mochi_options" : {
            "cert_path" : "--certificate-path=tests/certs",
            "autorun" : "--autorun",
            "close_when_done" : "--close-when-done",
            "console_level" : "--console-level=INFO",
        },

        'xpcshell_name' : XPCSHELL_NAME,
        #global xpcshell options
        'global_xpcshell_options' : {
            'manifest' : '--manifest=tests/xpcshell/tests/all-test-dirs.list',
            'xpcshell_name' : 'application/firefox/' + XPCSHELL_NAME
        },

        #local mochi suites
        "all_mochi_suites" :
        {
            'plain1' : ["--total-chunks=5", "--this-chunk=1", "--chunk-by-dir=4"],
            'plain2' : ["--total-chunks=5", "--this-chunk=2", "--chunk-by-dir=4"],
            'plain3' : ["--total-chunks=5", "--this-chunk=3", "--chunk-by-dir=4"],
            'plain4' : ["--total-chunks=5", "--this-chunk=4", "--chunk-by-dir=4"],
            'plain5' : ["--total-chunks=5", "--this-chunk=5", "--chunk-by-dir=4"],
            'chrome' : ["--chrome"],
            'browser-chrome' : ["--browser-chrome"],
            # 'a11y' : ["--a11y"], no a11y for mac os x
            'plugins' : ["--setpref='dom.ipc.plugins.enabled=false'",
                "--test-path='modules/plugin/test'"]
        },

        #local reftests suites
        "all_reftest_suites" :
        {
            'reftest' : ["tests/reftest/tests/layout/reftests/reftest.list"],
            'crashtest' : ["tests/reftest/tests/layout/reftests/crashtests.list"],
            'jsreftest' : ["--extra-profile-file=tests/jsreftest/tests/user.js", "tests/jsreftests/jstests.list"],
        },


        "preflight_run_cmd_suites" : [
                {
                    'name' : 'disable_screen_saver',
                    'cmd' : ['xset', 's', 'reset'],
                    'enabled' : DISABLE_SCREEN_SAVER
                },
                {
                    'name' : 'adjust_screen_resolution',
                    'cmd' : [
                        'bash', '-c', 'screenresolution', 'get', '&&', 'screenresolution',
                        'list', '&&', 'system_profiler', 'SPDisplaysDataType'
                    ],
                    'enabled' : ADJUST_SCREEN_RESOLUTION
                },
        ],

}

