CLOBBERER_URL = 'http://clobberer.pvt.build.mozilla.org/index.php'
STAGE_PRODUCT = 'firefox'
# TODO move stage_server to a production/staging/etc sep config
# /buildbot-configs/mozilla/preproduction_config.py
# 'stage_server': 'preproduction-stage.srv.releng.scl3.mozilla.com',
# /buildbot-configs/mozilla/production_config.py
# 'stage_server': 'stage.mozilla.org',
# /buildbot-configs/mozilla/staging_config.py
STAGE_SERVER = 'dev-stage01.srv.releng.scl3.mozilla.com'
# TODO Reminder, stage_username and stage_ssh_key differ on Try
STAGE_USERNAME = 'ffxbld'
STAGE_SSH_KEY = 'ffxbld_dsa'

config = {
    # TODO move download_base_url to a production/staging/etc sep config
    # /buildbot-configs/mozilla/preproduction_config.py
    # 'download_base_url': 'http://preproduction-stage.srv.releng.
    # scl3.mozilla.com/pub/mozilla.org/firefox/nightly',
    # /buildbot-configs/mozilla/production_config.py
    # 'download_base_url':
    # 'http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly',
    # /buildbot-configs/mozilla/staging_config.py
    'download_base_url': 'http://dev-stage01.srv.releng.scl3.mozilla.com/pub/\
mozilla.org/firefox/nightly',
    # if false, only clobber 'abs_work_dir'
    # if true: possibly clobber, clobberer, and purge_builds
    # see PurgeMixin for clobber() conditions
    'clobberer_url': CLOBBERER_URL,  # we wish to clobberer
    'periodic_clobber': 168,  # default anyway but can be overwritten

    # hg tool stuff
    'default_vcs': 'hgtool',
    # decides whether we want to use moz_sign_cmd in env
    'enable_signing': True,
    "repos": [{"repo": "http://hg.mozilla.org/users/jlund_mozilla.com/tools"}],
    "buildbot_json_path": "buildprops.json",
    'default_actions': [
        'clobber',
        'pull',
        'setup-mock',
        'build',
        'generate-build-properties',
        'generate-build-stats',
        'make-and-upload-symbols',
        'make-packages',
        'make-upload',
        'test-pretty-names',
        'check-test-complete',
        'enable-ccache',
    ],
    'exes': {
        "buildbot": "/tools/buildbot/bin/buildbot",
    },
    'purge_skip': ['info', 'rel-*:45d', 'tb-rel-*:45d'],
    'purge_basedirs':  ["/mock/users/cltbld/home/cltbld/build"],
    # mock shtuff
    'use_mock':  True,
    'mock_mozilla_dir':  '/builds/mock_mozilla',
    'mock_target': 'mozilla-centos6-x86_64',
    'mock_pre_package_copy_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data'),
        ('/tools/tooltool.py', '/builds/tooltool.py'),
    ],
    'mock_pre_package_cmds': [
        'mkdir -p /builds/slave/m-cen-lx-000000000000000000000/build'
    ],
    'enable_ccache': True,
    'ccache_env': {
        'CCACHE_BASEDIR': "%(base_dir)s",
        'CCACHE_COMPRESS': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_HASHDIR': '',
        'CCACHE_UMASK': '002',
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
    'enable_package_tests': True,
    'stage_product': STAGE_PRODUCT,
    "enable_talos_sendchange": True,
    "l10n_check_test": True,
    'upload_symbols': True,

    'stage_server': STAGE_SERVER,
    'stage_username': STAGE_USERNAME,
    'stage_ssh_key': STAGE_SSH_KEY,
    'upload_env': {
        'UPLOAD_HOST': STAGE_SERVER,
        'UPLOAD_USER': STAGE_USERNAME,
        'UPLOAD_TO_TEMP': '1',
        'UPLOAD_SSH_KEY': '~/.ssh/%s' % (STAGE_SSH_KEY,),
    },
    'update_env': {
        'MAR': '../dist/host/bin/mar',
        'MBSDIFF': '../dist/host/bin/mbsdiff'
    },
    'latest_mar_dir': '/pub/mozilla.org/%s/nightly/latest-%%(branch)s' % (
        STAGE_PRODUCT,)

    # for testing, here is my master
    "sendchange_masters": ["dev-master01.build.scl1.mozilla.com:8038"],
    # production.py
    # "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    # staging
    # 'dev-master01.build.scl1.mozilla.com:9901'
    # pre production
    # 'preproduction-master.srv.releng.scl3.mozilla.com:9008'
    # production.py
    # "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    # staging
    # 'dev-master01.build.scl1.mozilla.com:9901'
    # pre production
    # 'preproduction-master.srv.releng.scl3.mozilla.com:9008'
    # if staging/preproduction we should have this key:
    "graph_server_branch_name": "MozillaTest",
    # else if production we let buildbot props decide in
    # self._query_graph_server_branch_name()
    ##############



    ###### 32 bit specific ######
    # TODO find out if we need all these platform keys
    # TODO port self.platform_variation self.complete_platform for RPM check
    'platform': 'linux',
    # 'platform_variation': '',
    # 'complete_platform': 'linux',
    # 'stage_platform': 'linux64',
    'platform_ftp_name': 'linux-i686.complete.mar',
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': 'obj-firefox',
        # not sure if this will always be server host
        'SYMBOL_SERVER_HOST': "symbolpush.mozilla.org",
        'SYMBOL_SERVER_USER': 'ffxbld',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'SYMBOL_SERVER_SSH_KEY': "/home/mock_mozilla/.ssh/ffxbld_dsa",
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'TINDERBOX_OUTPUT': '1',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_COMPRESS': '1',
        'CCACHE_UMASK': '002',
        'LC_ALL': 'C',
        # 32 bit specific
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib/ccache:\
/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:\
/tools/python27/bin:/tools/python27-mercurial/bin:/home/cltbld/bin',
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
production/mozilla2/linux/%(branch)s/nightly/mozconfig',

    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux32/\
releng.manifest",
    'package_filename': '*.linux-i686*.tar.bz2',

    "check_test_env": {
        'MINIDUMP_STACKWALK': 'breakpad/linux/minidump_stackwalk',
        'MINIDUMP_SAVE_PATH': 'minidumps',
    },
    'base_name': 'Linux_%(branch)s',
    ##############################
}
