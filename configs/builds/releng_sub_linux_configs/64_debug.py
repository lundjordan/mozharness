MOZ_OBJDIR = 'obj-firefox'

config = {
    'default_actions': [
        'read-buildbot-config',
        'clobber',
        'pull',
        'setup-mock',
        'checkout-source',
        'build',
        'generate-build-properties',
        # 'generate-build-stats', debug does not do this action
        'make-build-symbols',
        'make-packages',
        'make-upload',
        # 'test-pretty-names', debug does not do this action
        'check-test-complete',
        'enable-ccache',
    ],
    'purge_minsize': 14,
    'mock_pre_package_copy_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data'),
    ],
    "enable_talos_sendchange": False,  # debug does not fire a talos sendchange
    'enable_signing': False,

    #### 64 bit build specific #####
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': MOZ_OBJDIR,
        # not sure if this will always be server host
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_COMPRESS': '1',
        'CCACHE_UMASK': '002',
        'LC_ALL': 'C',
        'XPCOM_DEBUG_BREAK': 'stack-and-abort',
        # 64 bit specific
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:\
/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:\
/tools/python27-mercurial/bin:/home/cltbld/bin',
        'LD_LIBRARY_PATH': '/tools/gcc-4.3.3/installed/lib64:\
%s/dist/bin' % (MOZ_OBJDIR,),
    },
    'src_mozconfig': 'browser/config/mozconfigs/linux64/debug',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/\
production/mozilla2/linux64/mozilla-central/debug/mozconfig',
    'base_name': 'Linux x86-64 %(branch)s leak test',
    #######################
}
