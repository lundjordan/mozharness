BASE = 'http://ftp.mozilla.org/pub/mozilla.org/firefox'
# LOCATION = 'tinderbox-builds' # e.g. 'nightly', 'tryserver-builds', 'releases'
# BRANCH = 'mozilla-central'
# OS = 'linux64'
# TYPE = '' #TYPE='-debug'
# ID = '/1335348407'

# TODO support all FTPS: right now this format is for tinderbox-builds
# eg: http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-central-linux64/1335797980/
FTP = BASE + "/{LOCATION}/{BRANCH}-{OS}{TYPE}{ID}"

# OS_ARCH eg: 'linux-x86_64'
# OS_EXTENSION eg: 'tar.bz2'
BINARY = "firefox-{version}.en-US.{OS_ARCH}.{OS_EXTENSION}"
TESTS = "firefox-{version}.en-US.{OS_ARCH}.tests.zip"

config = {

        # for develepors in future. Not implemented yet.
        "url_base" : FTP,
        "file_archives" : {"bin_archive" : BINARY, "tests_archive" :  TESTS},

        #global unittest options
        "global_test_options" : {
            "app_path" : "--appname=firefox/{app_name}",
            "util_path" : "--utility-path=bin",
            "extra_prof_path" : "--extra-profile-file=bin/plugins",
            "symbols_path" : "--symbols-path=symbols"
            },

        #global mochitest options
        "mochi_run_dir" : "mochitest",
        "global_mochi_options" : {
            "cert_dir" : "--certificate-path=certs",
            "autorun" : "--autorun",
            "close_when_done" : "--close-when-done",
            "console_level" : "--console-level=INFO",
            },
        #local mochi tests
        "all_mochi_suites" :
        {
            'plain1' : ["--total-chunks=5", "--this-chunk=1", "--chunk-by-dir=4"],
            'plain2' : ["--total-chunks=5", "--this-chunk=2", "--chunk-by-dir=4"],
            'plain3' : ["--total-chunks=5", "--this-chunk=3", "--chunk-by-dir=4"],
            'plain4' : ["--total-chunks=5", "--this-chunk=4", "--chunk-by-dir=4"],
            'plain5' : ["--total-chunks=5", "--this-chunk=5", "--chunk-by-dir=4"],
            'chrome' : ["--chrome"],
            'browser-chrome' : ["--browser-chrome"],
            'a11y' : ["--a11y"],
            # TODO pretify this last mochtest when you figure out what it does ;)
            'plugins' : ["--setpref='dom.ipc.plugins.enabled=false'",
                "--test-path='modules/plugin/test'"]
        },

        #global reftests params
        "reftest_run_dir" : "reftest",

        "all_reftest_suites" :
        {
            'reftest' : ["reftest/tests/layout/reftests/reftest.list"],
            'crashtest' : ["reftest/tests/layout/reftests/crashtests.list"],
            'jsreftest' : ["--extra-profile-file=jsreftest/tests/user.js", "jsreftests/jstests.list"],
        },

        # TODO xpcshell
        # "firefox_plugins_dir" : "firefox/plugins"

}
