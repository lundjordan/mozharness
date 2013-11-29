MOZ_OBJDIR = 'obj-firefox'

config = {
    'default_actions': [
        'clobber',
        'pull',
        'setup-mock',
        'build',
        'generate-build-properties',
        # 'generate-build-stats', stat debug does not do this action
        # 'make-build-symbols', stat debug does not do this action
        'make-packages',
        'make-upload',
        # 'test-pretty-names', stat debug does not do this action
        # 'check-test-complete', stat debug does not do this action
        'enable-ccache',
    ],
    'mock_pre_package_copy_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data'),
    ],
    "enable_talos_sendchange": False,  # stat debug doesn't do talos sendchange
    # stat debug doesn't do unittest sendchange or make package-tests
    'enable_package_tests': False,
    'enable_signing': False,
    'purge_minsize': 12,
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux64/\
clang.manifest",

    #### 64 bit build specific #####
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': MOZ_OBJDIR,
        # not sure if this will always be server host
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
        'XPCOM_DEBUG_BREAK': 'stack-and-abort',
        # 64 bit specific
        'MOZ_SYMBOLS_EXTRA_BUILDID': 'linux64-st-an-debug',
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:\
/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:\
/tools/python27-mercurial/bin:/home/cltbld/bin',
    },
    'src_mozconfig': 'browser/config/mozconfigs/linux64/\
debug-static-analysis-clang',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/\
production/mozilla2/in_tree/mozconfig',
    'base_name': 'Linux x86-64 %(branch)s debug static analysis',
    #######################
}
