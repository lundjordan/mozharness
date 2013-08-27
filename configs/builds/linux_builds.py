#!/usr/bin/env python

config = {
    # for def pull()
    # "repos": [{"repo": "http://hg.mozilla.org/build/tools"}],
    "buildbot_json_path": "buildprops.json",

    'default_actions': [
        'read-buildbot-config',
        'clobber',
        'setup-mock',
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
        'CCACHE_BASEDIR': "{base_dir}",
        'CCACHE_COMPRESS': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_HASHDIR': '',
        'CCACHE_UMASK': '002'
    },

    'objdir': 'obj-firefox',
    'old_packages': [
        "{objdir}/dist/firefox-*",
        "{objdir}/dist/fennec*",
        "{objdir}/dist/seamonkey*",
        "{objdir}/dist/thunderbird*",
        "{objdir}/dist/install/sea/*.exe"
    ]
}
