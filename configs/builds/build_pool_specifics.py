# this is a dict of pool specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

config = {
    "staging": {
        "sendchange_masters": ["dev-master1.srv.releng.scl3.mozilla.com:9038"],
        # XXX: should point at aus4-admin-dev once production is pointing
        # elsewhere
        'balrog_api_root': 'https://aus4-admin-dev.allizom.org',
        'balrog_username': 'stage-ffxbld',
        'download_base_url': 'http://dev-stage01.srv.releng.scl3.mozilla'
                             '.com/pub/mozilla.org/firefox/nightly',
        'aus2_ssh_key': 'ffxbld_dsa',
        'aus2_user': 'ffxbld',
        'aus2_host': 'dev-stage01.srv.releng.scl3.mozilla.com',
        'stage_server': 'dev-stage01.srv.releng.scl3.mozilla.com',
        'symbol_server_host': "dev-stage01.srv.releng.scl3.mozilla.com",
        # staging we should use MozillaTest
        # but in production we let the self.branch decide via
        # self._query_graph_server_branch_name()
        "graph_server_branch_name": "MozillaTest",
        "hgtool_base_bundle_urls": [
            'http://dev-stage01.build.mozilla.org/pub/mozilla'
            '.org/firefox/bundles',
        ],
    },
    "production": {
        "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
        'balrog_api_root': 'https://aus4-admin.mozilla.org',
        'balrog_username': 'ffxbld',
        'download_base_url': 'http://ftp.mozilla.org/pub/mozilla'
                             '.org/firefox/nightly',
        'aus2_host': 'aus3-staging.mozilla.org',
        'aus2_ssh_key': 'auspush',
        'aus2_user': 'ffxbld',
        'stage_server': 'stage.mozilla.org',
        'symbol_server_host': "symbolpush.mozilla.org",
        "hgtool_base_bundle_urls": [
            'https://ftp-ssl.mozilla.org/pub/mozilla.org/firefox/bundles'
        ],
    },
}
