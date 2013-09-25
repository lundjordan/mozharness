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
        # 32 bit specific
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib/ccache:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/tools/python27-mercurial/bin:/home/cltbld/bin',
        'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib",
    },
    'purge_minsize': 12,

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
        ######## 32 bit specific ###########
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
        ######## 32 bit specific ###########
    ],
    'src_mozconfig': 'browser/config/mozconfigs/linux32/nightly',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/\
production/mozilla2/linux/mozilla-central/nightly/mozconfig',

    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux32/\
releng.manifest",
    'package_filename': '*.linux-i686*.tar.bz2',
    'stage_platform': 'linux',

    "check_test_env": {
        'MINIDUMP_STACKWALK': 'breakpad/linux/minidump_stackwalk',
        'MINIDUMP_SAVE_PATH': 'minidumps',
    },
}
