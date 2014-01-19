# this is a dict of branch specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

config = {
    "mozilla-central": {
        "update_channel": "nightly",
        "create_snippets": True,
        "create_partial": True,
        "graph_server_branch_name": "Firefox",
    }
}
