config = {
    'default_actions': [
        'clobber',
        'clone-tools',
        'setup-mock',
        'build',
        'update',  # decided by query_is_nightly()
    ],
    'stage_platform': 'linux64-nonunified',
    #### 64 bit build specific #####
    'src_mozconfig': 'browser/config/mozconfigs/linux64/nightly-nonunified',
    #######################
}
