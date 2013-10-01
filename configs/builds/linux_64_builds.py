config = {
    "repos": [{"repo": "http://hg.mozilla.org/users/jlund_mozilla.com/tools"}],
    "buildbot_json_path": "buildprops.json",
    'default_actions': [
        'read-buildbot-config',
        'clobber',
        'pull',
        'setup-mock',
        'checkout-source',
        'build',
        'generate-build-properties',
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
    'base_name': 'Linux %(branch)s',
    'enable_package_tests': True,
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
    # TODO find out if we need platform keys in config or if buildbot_config
    # will do
    # 'platform': 'linux',
    # # this will change for sub configs like asan, pgo etc
    # 'complete_platform': 'linux',

    # for testing, here is my master
    "sendchange_masters": ["dev-master01.build.scl1.mozilla.com:8038"],
    # production.py
    # "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    # staging
    # 'dev-master01.build.scl1.mozilla.com:9901'
    # pre production
    # 'preproduction-master.srv.releng.scl3.mozilla.com:9008'
    "pretty_name_pkg_targets": ["package"],
    "l10n_check_test": True,


    ###### 64 bit specific ######
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
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:\
/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:\
/tools/python27-mercurial/bin:/home/cltbld/bin',
        'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib64",
        ##
    },
    'purge_minsize': 14,
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
    'base_name': 'Linux_x86-64_%(branch)s',
    ##############################
}
