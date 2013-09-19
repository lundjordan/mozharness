#### architecture differences ####
# TODO ADD THE BITS TO SCRIPT ARGS

ENV = {
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
}
# if platform.architecture()[0] == '64bit':
# ENV.update({
#     'MOZ_SYMBOLS_EXTRA_BUILDID': 'linux64',
#     'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:/\
# usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/\
# tools/python27-mercurial/bin:/home/cltbld/bin'
    # 'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib64",
# })
# ARCH_MOCK_PACKAGES = [
#     'glibc-static', 'libstdc++-static',
#     'gtk2-devel', 'libnotify-devel',
#     'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
#     'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
#     'GConf2-devel',
#     ### from releng repo
#     'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
#     'yasm', 'ccache',
#     ###
#     'pulseaudio-libs-devel', 'gstreamer-devel',
#     'gstreamer-plugins-base-devel', 'freetype-2.3.11-6.el6_1.8.x86_64',
#     'freetype-devel-2.3.11-6.el6_1.8.x86_64'
# ]
# else:
ENV.update({
    'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib/ccache:/bin:/usr/\
bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/\
tools/python27-mercurial/bin:/home/cltbld/bin',
    'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib",
})
ARCH_MOCK_PACKAGES = [
    'glibc-static.i686', 'libstdc++-static.i686',
    'gtk2-devel.i686', 'libnotify-devel.i686',
    'alsa-lib-devel.i686', 'libcurl-devel.i686',
    'wireless-tools-devel.i686', 'libX11-devel.i686',
    'libXt-devel.i686', 'mesa-libGL-devel.i686',
    'gnome-vfs2-devel.i686', 'GConf2-devel.i686'
    'pulseaudio-libs-devel.i686',
    'gstreamer-devel.i686', 'gstreamer-plugins-base-devel.i686',
    # Packages already installed in the mock environment, as x86_64
    # packages.
    'glibc-devel.i686', 'libgcc.i686', 'libstdc++-devel.i686',
    # yum likes to install .x86_64 -devel packages that satisfy .i686
    # -devel packages dependencies. So manually install the dependencies
    # of the above packages.
    'ORBit2-devel.i686', 'atk-devel.i686', 'cairo-devel.i686',
    'check-devel.i686', 'dbus-devel.i686', 'dbus-glib-devel.i686',
    'fontconfig-devel.i686', 'glib2-devel.i686',
    'hal-devel.i686', 'libICE-devel.i686', 'libIDL-devel.i686',
    'libSM-devel.i686', 'libXau-devel.i686', 'libXcomposite-devel.i686',
    'libXcursor-devel.i686', 'libXdamage-devel.i686',
    'libXdmcp-devel.i686', 'libXext-devel.i686', 'libXfixes-devel.i686',
    'libXft-devel.i686', 'libXi-devel.i686', 'libXinerama-devel.i686',
    'libXrandr-devel.i686', 'libXrender-devel.i686',
    'libXxf86vm-devel.i686', 'libdrm-devel.i686', 'libidn-devel.i686',
    'libpng-devel.i686', 'libxcb-devel.i686', 'libxml2-devel.i686',
    'pango-devel.i686', 'perl-devel.i686', 'pixman-devel.i686',
    'zlib-devel.i686',
    # Freetype packages need to be installed be version, because a newer
    # version is available, but we don't want it for Firefox builds.
    'freetype-2.3.11-6.el6_1.8.i686',
    'freetype-devel-2.3.11-6.el6_1.8.i686',
    'freetype-2.3.11-6.el6_1.8.x86_64',
]
#####

config = {
    # for def pull()
    "repos": [{"repo": "http://hg.mozilla.org/build/tools"}],
    "buildbot_json_path": "buildprops.json",

    'default_actions': [
        'read-buildbot-config',
        'clobber',
        'pull',
        'setup-mock',
        'checkout-source',
        'build',
        'generate-build-stats',
        'make-build-symbols',
        'make-packages',
        'make-upload',
        'test-pretty-names',
        'check-test-complete',
        'enable-ccache',
    ],

    'exes': {
        "buildbot": "/tools/buildbot/bin/buildbot",
    },

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
    'mock_packages': ARCH_MOCK_PACKAGES + [
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
    ],


    'enable_ccache': True,
    'ccache_env': {
        'CCACHE_BASEDIR': "%(base_dir)s",
        'CCACHE_COMPRESS': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_HASHDIR': '',
        'CCACHE_UMASK': '002',
    },
    'env': ENV,

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

    # TODO XXX MOZCONFIG PATHS DIFFER DEPENDING ON BITS
    'src_mozconfig': 'browser/config/mozconfigs/linux32/nightly',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/\
production/mozilla2/linux/mozilla-central/nightly/mozconfig',

    # TODO XXX manifest differs on bits
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux32/\
releng.manifest",
    'tooltool_url_list': [
        "http://runtime-binaries.pvt.build.mozilla.org/tooltool"
    ],
    'tooltool_script': "/tools/tooltool.py",
    'tooltool_bootstrap': "setup.sh",

    # in linux we count ctors
    'enable_count_ctors': True,

    'graph_server': 'graphs.allizom.org',
    'graph_selector': '/server/collect.cgi',
    'graph_branch': 'MozillaTest',
    'base_name': 'Linux %(branch)s',

    'enable_symbols': True,
    'enable_package_tests': True,
    'package_filename': '*.linux-i686*.tar.bz2',
    # 'packageFilename': '*.linux-x86_64*.tar.bz2',

    # TODO port self.platform_variation self.complete_platform for RPM check

    'upload_env': {
        # TODO ADD SEPARATE CONFIGS ?
        # /buildbot-configs/mozilla/preproduction_config.py
        # 'stage_server': 'preproduction-stage.srv.releng.scl3.mozilla.com',
        # /buildbot-configs/mozilla/production_config.py
        # 'stage_server': 'stage.mozilla.org',
        # /buildbot-configs/mozilla/staging_config.py
        'UPLOAD_HOST': 'dev-stage01.srv.releng.scl3.mozilla.com',
        # TODO I think upload_user differs on TRY branch
        'UPLOAD_USER': 'ffxbld',
        'UPLOAD_TO_TEMP': '1',
        'UPLOAD_SSH_KEY': '~/.ssh/ffxbld_dsa',
    },

    'stage_product': 'firefox',
    'stage_platform': 'linux',

    # TODO find out if we need platform keys in config or if buildbot_config
    # will do
    # 'platform': 'linux',
    # # this will change for sub configs like asan, pgo etc
    # 'complete_platform': 'linux',

    # production.py
    "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    # staging
    # 'dev-master01.build.scl1.mozilla.com:9901'
    # pre production
    # 'preproduction-master.srv.releng.scl3.mozilla.com:9008'

    "pretty_name_pkg_targets": ["package"],
    "l10n_check_test": True,

    "check_test_env": {
        'MINIDUMP_STACKWALK': 'breakpad/linux/minidump_stackwalk',
        'MINIDUMP_SAVE_PATH': 'minidumps',
    },


}
