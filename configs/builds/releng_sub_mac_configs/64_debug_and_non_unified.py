import os

MOZ_OBJDIR = 'obj-firefox'

config = {
    'default_actions': [
        'clobber',
        'clone-tools',
        # 'setup-mock',
        'build',
        # 'upload',
        # 'sendchanges',
        # 'generate-build-stats',
        'update',  # decided by query_is_nightly()
    ],
    'debug_build': True,
    'stage_platform': 'macosx64-debug-nonunified',
    'enable_talos_sendchange': False,
    'enable_unittest_sendchange': False,
    'objdir': 'obj-firefox',
    #### 64 bit build specific #####
    'env': {
        'MOZBUILD_STATE_PATH': os.path.join(os.getcwd(), '.mozbuild'),
        'MOZ_AUTOMATION': '1',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': 'obj-firefox',
        'TINDERBOX_OUTPUT': '1',
        'TOOLTOOL_CACHE': '/builds/tooltool_cache',
        'TOOLTOOL_HOME': '/builds',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_COMPRESS': '1',
        'CCACHE_UMASK': '002',
        'LC_ALL': 'C',
        'XPCOM_DEBUG_BREAK': 'stack-and-abort',
        ## 64 bit specific
        'PATH': '/tools/python/bin:/tools/buildbot/bin:/opt/local/bin:/usr/bin:'
                '/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin',
        ##
    },
    'src_mozconfig': 'browser/config/mozconfigs/macosx64/debug-nonunified',
    #######################
}
