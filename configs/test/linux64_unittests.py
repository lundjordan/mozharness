BASE = 'http://ftp.mozilla.org/pub/mozilla.org/firefox'
LOCATION = 'tinderbox-builds' # e.g. 'nightly', 'tryserver-builds', 'releases'
BRANCH = 'mozilla-central'
OS = 'linux64'
TYPE = '' #TYPE='-debug'
#TODO ARRRGG get this ID dynamically...
ID = '/1335348407'
FTP = BASE + "/" + LOCATION + "/" + BRANCH + "-" + OS + TYPE + ID

OS_ARCH = 'linux-x86_64'
OS_EXTENSION = 'tar.bz2'
BINARY = "firefox-{version}.en-US." + OS_ARCH + "." + OS_EXTENSION
TESTS = "firefox-{version}.en-US." + OS_ARCH + ".tests.zip"

config = {
        "os" : OS,
        "branch" : BRANCH,
        "url_base" : FTP,
        "file_archives" : { "bin_archive" : BINARY, "tests_archive" :  TESTS},
        "extract_tool" : {"tool" : "tar", "flags" : "-jxvf"},

        #global unittest options
        "unittest_paths" : {
            "app_name" : "firefox/firefox",
            "util_path" : "bin",
            "extra_prof_path" : "bin/plugins",
            "symbols_path" : "symbols"
            },

        "mochi_path" : "mochitest",

        #global mochitest options
        "mochi_configs" : {
            "cert_dir" : "certs",
            "autorun" : "--autorun",
            "close_when_done" : "--close-when-done",
            #TODO look at logging of how console_level behaves
            "console_level" : "INFO",
            },

        #local mochi tests
        "mochi_individual_options" : [
            ["--total-chunks=5", "--this-chunk=1", "--chunk-by-dir=4"],
            ["--chrome"], ["--browser-chrome"], ["--a11y"],
            # TODO pretify this last mochtest when you figure out what it does ;)
            ["--setpref='dom.ipc.plugins.enabled=false'",
                "--test-path='modules/plugin/test'"]
        ],

        #global reftests params

        "reftest_configs" : {
            "reftest_path" : "reftest",
            "reftest_layout_dir" : "reftest/tests/layout/reftests",
            "jsreftest_test_dir" : "jsreftest/tests",

            "reftest_list_options" : [],
            "reftest_crashlist_options" : [],
            "jstests_options" : [
                "--extra-profile-file=jsreftest/tests/user.js",
            ]

        },
        "firefox_plugins_dir" : "firefox/plugins"

}
