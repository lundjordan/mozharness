# this is a dict of branch specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

config = {
    "mozilla-central": {
        "update_channel": "nightly",
        "create_snippets": True,
        "create_partial": True,
        "graph_server_branch_name": "Firefox",
        "repo_path": 'mozilla-central',
        'use_branch_in_symbols_extra_buildid': True,
    }
}
