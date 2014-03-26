# this is a dict of branch specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

# we should be able to port this in-tree and have the respective repos and
# revisions handle what goes on in here. Tracking: bug 978510

# example config and explanation of how it works:
# config = {
#     # if a branch matches a key below, override items in self.config with
#     # items in the key's value.
#     # this override can be done for every platform or at a platform level
#     '<branch-name>': {
#         # global config items (applies to all platforms and build types)
#         'repo_path': "projects/<branch-name>",
#         'graph_server_branch_name': "Firefox",
#
#         # platform config items (applies to specific platforms)
#         'platform_overrides': {
#             # if a platform matches a key below, override items in
#             # self.config with items in the key's value
#             'linux64-debug': {
#                 'upload_symbols': False,
#             },
#             'win64': {
#                 'no_actions': ['check-test']
#             },
#         }
#     },
# }

config = {
    "mozilla-central": {
        "update_channel": "nightly",
        "graph_server_branch_name": "Firefox",
        "repo_path": 'mozilla-central',  # 'mozilla-central' is the default
        'use_branch_in_symbols_extra_buildid': False,
    },
    "cypress": {
        # for branches that are pretty similar to m-c and only require a
        # slight change like 'repo_path', we may not need an item for each
        "repo_path": 'projects/cypress',
    },
    'fx-team': {
        'repo_path': 'integration/fx-team',
    },
    'mozilla-inbound': {
        'repo_path': 'integration/mozilla-inbound',
    },
    'b2g-inbound': {
        'repo_path': 'integration/b2g-inbound',
        'platform_overrides': {
            'win32': {
                'enable_checktests': False,
            },
            'win32-debug': {
                'enable_checktests': False,
            },
            'macosx64': {
                'enable_checktests': False,
            },
            'macosx64-debug': {
                'enable_checktests': False,
            },
        },
    },
    'services-central': {
        'repo_path': 'services/services-central',
    },
    'ux': {
        "graph_server_branch_name": "UX",
    },
    'birch': {
        'enable_merging': False,
        'pgo_strategy': 'periodic',
        'enable_nightly': True,
        'create_snippet': True,
        'create_mobile_snippet': True,
        'enable_l10n': True,
        'enable_l10n_onchange': False,
        'l10n_platforms': ['linux', 'linux64'],
        'l10n_tree': 'fxcentral',
        'l10n_repo_path': 'l10n-central',
        'enUS_binaryURL': '/nightly/latest-birch',
        'enable_valgrind': False,
        'branch_projects': [],
        'enable_nightly': False,
        'lock_platforms': True,
        'platforms': {
            'linux': {
                'enable_opt_unittests': False,
                'enable_debug_unittests': False,
                'talos_slave_platforms': [],
                },
            'linux-debug': {},
            'linux64': {
                'enable_opt_unittests': False,
                'enable_debug_unittests': False,
                'talos_slave_platforms': [],
                },
            'linux64-debug': {},
            }
    },
    'cedar': {
        'mozharness_tag': 'default',
        'enable_talos': True,
        'talos_suites': {
            'xperf': 1,
            'tp5o-metro': 1,
            'other-metro': 1,
            'svgr-metro': 1,
            'dromaeojs-metro': 1,
            },
        'enable_opt_unittests': True,
        'mobile_platforms': {
            'android-x86': {
                'enable_opt_unittests': True,
                },
            },
        },
    'date': {
        'lock_platforms': True,
        'platforms': {
            'win32': {
                'enable_opt_unittests': True,
                },
            'win64': {
                'enable_opt_unittests': True,
                'slave_platforms': ['win64_vm', 'win8_64'],
                },
            'win64-debug': {
                'enable_debug_unittests': True,
                },
            },
        'enable_merging': False,
        },
    'elm': {},
    'fig': {},
    'gum': {},
    'holly': {
        # Mimic mozilla-aurora
        'gecko_version': 29,
        'branch_projects': [],
        'pgo_strategy': 'periodic',
        'enable_nightly': True,
        'create_snippet': True,
        'create_partial': True,
        'platforms': {
            'linux': {
                'nightly_signing_servers': 'nightly-signing',
            },
            'linux64': {
                'nightly_signing_servers': 'nightly-signing',
            },
            'macosx64': {
                'nightly_signing_servers': 'mac-nightly-signing',
            },
            'win32': {
                'nightly_signing_servers': 'nightly-signing',
                },
        },
    },
    'jamun': {},
    'larch': {},
    'maple': {},
    # customizations for integration work for bugs 481815 and 307181
    'oak': {
        'enable_nightly': True,
        'create_snippet': True,
        'create_partial': True,
        'enable_talos': False,
        'platforms': {
            'linux': {
                'nightly_signing_servers': 'nightly-signing',
                },
            'linux64': {
                'nightly_signing_servers': 'nightly-signing',
                },
            'macosx64': {
                'nightly_signing_servers': 'mac-nightly-signing',
                },
            'win32': {
                'nightly_signing_servers': 'nightly-signing',
                },
            },
    },
    ### Not needed while booked for Thunderbird
    #'alder': {},
    ### Not needed whilst booked for bug 929203.
    #'pine': {}

    ### other branches that do not require anything special:
    # 'build-system': {}
    # 'graphics': {}
    # 'ionmonkey': {},
    'ash': {},
}
