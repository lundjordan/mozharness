BASE = 'http://ftp.mozilla.org/pub/mozilla.org/firefox'
LOCATION = 'tinderbox-builds' # e.g. 'nightly', 'tryserver-builds', 'releases'
BRANCH = 'mozilla-central'
OS = 'linux64'
TYPE = '' #TYPE='-debug'
FTP = BASE + "/" + LOCATION + "/" + BRANCH + "-" + OS + TYPE + "/" + "%(buildid)s"

OS_ARCH = 'linux-x86_64'
OS_EXTENSION = 'tar.bz2'
BINARY = "firefox-%(build_version)s.en-US." + OS_ARCH + "." + OS_EXTENSION
TESTS = "firefox-%(build_version)s.en-US." + OS_ARCH + ".tests.zip"

FTP_BINARY = FTP + "/" + BINARY
FTP_TESTS = FTP + "/" + TESTS

config = {
        "ftps" : [FTP_BINARY,  FTP_TESTS],
        "unzip_tool" : "tar -jxvf",
        "appname" : "firefox/firefox",

        #global unittest params
        "utility_path" : "bin",
        "extra_profile_dir" : "bin/plugins",
        "symbols_dir" : "symbols",

        #global mochitest params
        "certificate_path" : "certs",
        "autorun" : True,
        "close_when_done" : True,
        #TODO look at logging of how console_level behaves
        "console_level" : "INFO",

        #local mochi tests
        "mochi_tests" : ["--total-chunks=5 --this-chunk=1 --chunk-by-dir=4",
            "--chrome", "--browser-chrome", "--a11y",
            #TODO pretify this last mochtest when you figure out what it does ;)
            "--setpref='dom.ipc.plugins.enabled=false'" +
            "--test-path='modules/plugin/test'"],
        }
