BASE = 'http://ftp.mozilla.org/pub/mozilla.org/firefox'
# LOCATION = 'tinderbox-builds' # e.g. 'nightly', 'tryserver-builds', 'releases'
# BRANCH = 'mozilla-central'
# OS = 'linux64'
# TYPE = '' #TYPE='-debug'
# ID = '/1335348407'

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

        "repos": [{
            "repo": "http://hg.mozilla.org/build/tools",
            "revision": "default",
            "dest": "tools"
        }],

        # I will put these in configs in the case that someone wants to try one
        # of there own dirs
        "dirs" : {
            "reftest_dir" : "reftest",
            "mochi_dir" : "mochitest",
            "xpcshell_dir" : "xpcshell",
            "bin_dir" : "bin",
            "tools_dir" : "tools",
        },

        #global unittest options
        "global_test_options" : {
            "app_name" : "--appname={app_dir}{app_name}",
            "util_path" : "--utility-path={bin_dir}",
            "extra_prof_path" : "--extra-profile-file={bin_dir}/plugins",
            "symbols_path" : "--symbols-path={symbols_path}"
        },

        #global mochitest options
        "global_mochi_options" : {
            "cert_path" : "--certificate-path=certs",
            "autorun" : "--autorun",
            "close_when_done" : "--close-when-done",
            "console_level" : "--console-level=INFO",
        },

        #global xpcshell options
        'global_xpcshell_options' : {
            'symbols_path' : '--symbols-path={symbols_path}',
            'manifest' : '--manifest=xpcshell/tests/all-test-dirs.list',
            'xpcshell_name' : 'firefox/{xpcshell_name}'
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
            'a11y' : ["--a11y"],
            'plugins' : ["--setpref='dom.ipc.plugins.enabled=false'",
                "--test-path='modules/plugin/test'"]
        },

        #local reftests suites
        "all_reftest_suites" :
        {
            'reftest' : ["reftest/tests/layout/reftests/reftest.list"],
            'crashtest' : ["reftest/tests/layout/reftests/crashtests.list"],
            'jsreftest' : ["--extra-profile-file=jsreftest/tests/user.js", "jsreftests/jstests.list"],
        },


}
