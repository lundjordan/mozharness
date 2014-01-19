# this is a dict of pool specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

config = {
    "staging": {
    # for testing, here is my master
    "sendchange_masters": ["dev-master01.build.scl1.mozilla.com:8038"],
    # "sendchange_masters": ["dev-master01.build.scl1.mozilla.com:9901"],
    # XXX: should point at aus4-admin-dev once production is pointing elsewhere
    # # 'balrog_api_root': 'https://aus4-admin-dev.allizom.org',
    'download_base_url': 'http://dev-stage01.srv.releng.scl3.mozilla.com/pub/\
mozilla.org/firefox/nightly',
    # line 38 -- 'aus2_ssh_key': 'ffxbld_dsa',
    # line 37 -- 'aus2_user': 'ffxbld',
    # line 36 -- 'aus2_host': 'dev-stage01.srv.releng.scl3.mozilla.com',
        'stage_server': 'dev-stage01.srv.releng.scl3.mozilla.com',
    },
    "preproduction": {
    # "sendchange_masters": ["preproduction-master.srv.releng.scl3.mozilla.com:9008"],
    # XXX: should point at aus4-admin-dev once production is pointing elsewhere
    # # 'balrog_api_root': 'https://aus4-admin-dev.allizom.org',
    # 'download_base_url': 'http://preproduction-stage.srv.releng.
    # scl3.mozilla.com/pub/mozilla.org/firefox/nightly',
    # line 9 -- 'aus2_host': 'preproduction-stage.srv.releng.scl3.mozilla.com',
    # line 11 -- 'aus2_ssh_key': 'cltbld_dsa',
    # line 10 -- 'aus2_user': 'cltbld',
        'stage_server': 'preproduction-stage.srv.releng.scl3.mozilla.com',
    },
    "production": {
    # "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    # 'balrog_api_root': 'https://aus4-admin.mozilla.org',
    # 'download_base_url':
    # 'http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly',
    # line 59 -- 'aus2_host': 'aus3-staging.mozilla.org',
    # line 61 -- 'aus2_ssh_key': 'auspush',
    # line 60 -- 'aus2_user': 'ffxbld',
        'stage_server': 'stage.mozilla.org',
    },
}
