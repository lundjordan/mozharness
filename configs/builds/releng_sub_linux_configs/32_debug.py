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
        'make-build-symbols',
        'make-packages',
        'make-upload',
        'test-pretty-names',
        'check-test-complete',
        'enable-ccache',
    ],

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
        # 32 bit specific
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib/ccache:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/tools/python27-mercurial/bin:/home/cltbld/bin',
        'LD_LIBRARY_PATH': '/tools/gcc-4.3.3/installed/lib:%s/dist/bin' % (MOZ_OBJDIR,),
        'XPCOM_DEBUG_BREAK': 'stack-and-abort',
    },
    'purge_minsize': 14,

    #### 32 bit build specific #####
    'src_mozconfig': 'browser/config/mozconfigs/linux32/debug',
    'hg_mozconfig': 'http://hg.mozilla.org/build/buildbot-configs/raw-file/production/mozilla2/linux/mozilla-central/debug/mozconfig',
    'enable_signing': False,
}
