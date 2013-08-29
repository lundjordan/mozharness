#!/usr/bin/env python

config = {
    # for def pull()
    # "repos": [{"repo": "http://hg.mozilla.org/build/tools"}],
    "buildbot_json_path": "buildprops.json",

    'default_actions': [
        'read-buildbot-config',
        'clobber',
        'setup-mock',
        'checkout-source',
        'build'
    ],


    # we wish to purge builds
    'purge_minsize': 12,
    'purge_skip': ['info', 'rel-*:45d', 'tb-rel-*:45d'],
    'purge_basedirs':  ["/mock/users/cltbld/home/cltbld/build"],

    # mock stuff
    'use_mock':  True,
    'mock_mozilla_dir':  '/builds/mock_mozilla',
    'mock_target': 'mozilla-centos6-x86_64',
    'mock_pre_package_copy_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data')
    ],
    'mock_pre_package_cmds': [
        'mkdir -p /builds/slave/m-cen-lx-000000000000000000000/build'
    ],
    'mock_packages': [
        'autoconf213', 'python', 'zip', 'mozilla-python27-mercurial', 'git',
        'ccache', 'glibc-static', 'libstdc++-static', 'perl-Test-Simple',
        'perl-Config-General', 'gtk2-devel', 'libnotify-devel', 'yasm',
        'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
        'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
        'GConf2-devel', 'wget',
        'mpfr',  # required for system compiler
        'xorg-x11-font*',  # fonts required for PGO
        'imake',  # required for makedepend!?!
        ### from releng repo
        'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
        'yasm', 'ccache',
        ###
        'valgrind', 'pulseaudio-libs-devel', 'gstreamer-devel',
        'gstreamer-plugins-base-devel', 'freetype-2.3.11-6.el6_1.8.x86_64',
        'freetype-devel-2.3.11-6.el6_1.8.x86_64'
    ],

    'enable_ccache': True,
    'ccache_env': {
        'CCACHE_BASEDIR': "%(base_dir)s",
        'CCACHE_COMPRESS': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_HASHDIR': '',
        'CCACHE_UMASK': '002',
    },
    'env': {
        'HG_SHARE_BASE_DIR': "builds/hg-shared",
        'LC_ALL': "C",
        'CCACHE_COMPRESS': "1",
        'MOZ_SYMBOLS_EXTRA_BUILDID': "linux64",
        'SYMBOL_SERVER_HOST': "symbolpush.mozilla.org",
        'CCACHE_DIR': "builds/ccache",
        'POST_SYMBOL_UPLOAD_CMD': "usr/local/bin/post-symbol-upload.py",
        'MOZ_SIGN_CMD': "python /builds/slave/m-cen-l64-00000000000000000000/tools/release/signing/signtool.py --cachedir /builds/slave/m-cen-l64-00000000000000000000/signing_cache -t /builds/slave/m-cen-l64-00000000000000000000/token -n /builds/slave/m-cen-l64-00000000000000000000/nonce -c /builds/slave/m-cen-l64-00000000000000000000/tools/release/signing/host.cert -H signing4.srv.releng.scl3.mozilla.com:9110 -H signing5.srv.releng.scl3.mozilla.com:9110 -H signing6.srv.releng.scl3.mozilla.com:9110",
        'SYMBOL_SERVER_SSH_KEY': "home/mock_mozilla/.ssh/ffxbld_dsa",
        'DISPLAY': "2",
        'PATH': "tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/tools/python27-mercurial/bin:/home/cltbld/bin",
        'CCACHE_BASEDIR': "builds/slave/m-cen-l64-00000000000000000000",
        'TINDERBOX_OUTPUT': "1",
        'SYMBOL_SERVER_PATH': "mnt/netapp/breakpad/symbols_ffx/",
        'MOZ_OBJDIR': "obj-firefox",
        'MOZ_CRASHREPORTER_NO_REPORT': "1",
        'SYMBOL_SERVER_USER': "ffxbld",
        'LD_LIBRARY_PATH': "tools/gcc-4.3.3/installed/lib64",
        'CCACHE_UMASK': "002",
    },

    'vcs_share_base': '/builds/hg-shared',
    "hgtool_base_mirror_urls": [
        "http://hg-internal.dmz.scl3.mozilla.com"
    ],
    "hgtool_base_bundle_urls": [
        "http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles"
    ],

    'objdir': 'obj-firefox',
    'old_packages': [
        "%(objdir)s/dist/firefox-*",
        "%(objdir)s/dist/fennec*",
        "%(objdir)s/dist/seamonkey*",
        "%(objdir)s/dist/thunderbird*",
        "%(objdir)s/dist/install/sea/*.exe"
    ],
    # TODO support both 32 and 64 bit here
    'src_mozconfig': 'browser/config/mozconfigs/linux64/nightly',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/\
production/mozilla2/linux64/mozilla-central/nightly/mozconfig'
}
