CLOBBERER_URL = 'http://clobberer.pvt.build.mozilla.org/index.php'
STAGE_PRODUCT = 'firefox'
# TODO Reminder, stage_username and stage_ssh_key differ on Try
STAGE_USERNAME = 'ffxbld'
STAGE_SSH_KEY = 'ffxbld_dsa'

config = {
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

    # production.py
    # "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    # staging
    # 'dev-master01.build.scl1.mozilla.com:9901'
    # pre-production
    # 'preproduction-master.srv.releng.scl3.mozilla.com:9008'

    # TODO if staging/preproduction we should have this key:
    "graph_server_branch_name": "MozillaTest",
    # else if production we let buildbot props decide in
    # self._query_graph_server_branch_name()
    ##############


    ###### 64 bit specific ######
    # TODO find out if we need all these platform keys
    # TODO port self.platform_variation self.complete_platform for RPM check
    'platform': 'linux64',
    # # this will change for sub configs like asan, pgo etc
    # 'platform_variation': '',
    # 'complete_platform': 'linux',
    # 'stage_platform': 'linux64',
    'platform_ftp_name': 'linux-x86_64.complete.mar',
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
        'valgrind',
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
production/mozilla2/linux64/%(branch)s/nightly/mozconfig',
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux64/\
releng.manifest",
    'package_filename': '*.linux-x86_64*.tar.bz2',
    "check_test_env": {
        'MINIDUMP_STACKWALK': 'breakpad/linux64/minidump_stackwalk',
        'MINIDUMP_SAVE_PATH': 'minidumps',
    },
    'base_name': 'Linux_x86-64_%(branch)s',
    'update_platform': 'Linux_x86_64-gcc3',
    ##############################
}
