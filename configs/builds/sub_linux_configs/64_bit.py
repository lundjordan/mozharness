#### architecture differences ####

# if platform.architecture()[0] == '64bit':

config = {
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': 'obj-firefox',
        # not sure if this will always be server host
        'SYMBOL_SERVER_HOST': "symbolpush.mozilla.org",
        'SYMBOL_SERVER_USER': 'ffxbld',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'SYMBOL_SERVER_SSH_KEY': "/home/mock_mozilla/.ssh/ffxbld_dsa",
        'TINDERBOX_OUTPUT': '1',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_COMPRESS': '1',
        'CCACHE_UMASK': '002',
        'LC_ALL': 'C',
        ## 64 bit specific
        'MOZ_SYMBOLS_EXTRA_BUILDID': 'linux64',
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/tools/python27-mercurial/bin:/home/cltbld/bin'
        'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib64",
        ##
    },
    'mock_packages': [
        'autoconf213', 'python', 'zip', 'mozilla-python27-mercurial',
        'git', 'ccache', 'perl-Test-Simple', 'perl-Config-General',
        'yasm', 'wget',
        'mpfr',  # required for system compiler
        'xorg-x11-font*',  # fonts required for PGO
        'imake',  # required for makedepend!?!
        ### <-- from releng repo
        'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
        'yasm', 'ccache',
        ###
        'valgrind'
        ######## 64 bit specific ###########
        'glibc-static', 'libstdc++-static',
        'gtk2-devel', 'libnotify-devel',
        'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
        'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
        'GConf2-devel',
        ### from releng repo
        'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
        'yasm', 'ccache',
        ###
        'pulseaudio-libs-devel', 'gstreamer-devel',
        'gstreamer-plugins-base-devel', 'freetype-2.3.11-6.el6_1.8.x86_64',
        'freetype-devel-2.3.11-6.el6_1.8.x86_64'
    ],
    'src_mozconfig': 'browser/config/mozconfigs/linux64/nightly',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/\
production/mozilla2/linux64/mozilla-central/nightly/mozconfig',
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux64/\
releng.manifest",
    'package_filename': '*.linux-x86_64*.tar.bz2',
    'stage_platform': 'linux64',
    "check_test_env": {
        'MINIDUMP_STACKWALK': 'breakpad/linux64/minidump_stackwalk',
        'MINIDUMP_SAVE_PATH': 'minidumps',
    },
}
