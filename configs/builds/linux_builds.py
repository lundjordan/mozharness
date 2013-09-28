config = {
    # for def pull()
    "repos": [{"repo": "http://hg.mozilla.org/users/jlund_mozilla.com/tools"}],
    "buildbot_json_path": "buildprops.json",

    'default_actions': [
        'read-buildbot-config',
        'clobber',
        'pull',
        'setup-mock',
        'checkout-source',
        'build',
        'set_post_build_properties',
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
}
