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
}
