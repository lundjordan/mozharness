#!/usr/bin/env python

config = {
    # for def pull()
    # "repos": [{"repo": "http://hg.mozilla.org/build/tools"}],

    'default_actions': [
        'read-buildbot-config',
        'clobber',

        # use mock for Linux
        'reset-mock'
        'mock-init'
    ],

    'purge_basedirs':  ["/mock/users/cltbld/home/cltbld/build"],

    # mock stuff
    'use_mock':  True,
    'mock_mozilla_dir':  '/builds/mock_mozilla',
    'mock_target': 'mozilla-centos6-x86_64'
}
