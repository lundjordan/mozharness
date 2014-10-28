#!/usr/bin/env python
import os
config = {
    "default_actions": [
        'clobber',
        'checkout-sources',
        'get-blobs',
        'update-source-manifest',
        'build',
        'build-symbols',
        'make-updates',
        'prep-upload',
        'upload',
        'make-socorro-json',
        'upload-source-manifest',
    ],
    "upload": {
        "default": {
            "ssh_key": os.path.expanduser("~/.ssh/b2gbld_dsa"),
            "ssh_user": "b2gbld",
            "upload_remote_host": "pvtbuilds2.dmz.scl3.mozilla.com",
            "upload_remote_path": "/pub/mozilla.org/b2g/tinderbox-builds/%(branch)s-%(target)s/%(buildid)s",
            "upload_remote_symlink": "/pub/mozilla.org/b2g/tinderbox-builds/%(branch)s-%(target)s/latest",
            "upload_remote_nightly_path": "/pub/mozilla.org/b2g/nightly/%(branch)s-%(target)s/%(year)04i/%(month)02i/%(year)04i-%(month)02i-%(day)02i-%(hour)02i-%(minute)02i-%(second)02i",
            "upload_remote_nightly_path": "/pub/mozilla.org/b2g/nightly/%(branch)s-%(target)s/latest",
            "upload_dep_target_exclusions": [],
        },
        "public": {
            "ssh_key": os.path.expanduser("~/.ssh/ffxbld_rsa"),
            "ssh_user": "ffxbld",
            "upload_remote_host": "stage.mozilla.org",
            "post_upload_cmd": "post_upload.py --tinderbox-builds-dir %(branch)s-%(target)s -p b2g -i %(buildid)s --revision %(revision)s --release-to-tinderbox-dated-builds",
            "post_upload_nightly_cmd": "post_upload.py --tinderbox-builds-dir %(branch)s-%(target)s -b %(branch)s-%(target)s -p b2g -i %(buildid)s --revision %(revision)s --release-to-tinderbox-dated-builds --release-to-latest --release-to-dated",
        },
    },
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
    "gittool_share_base": "/builds/git-shared/git",
    "gittool_base_mirror_urls": [],
    "hgtool_share_base": "/builds/hg-shared",
    "hgtool_base_bundle_urls": ["https://ftp-ssl.mozilla.org/pub/mozilla.org/firefox/bundles"],
    "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    "exes": {
        "tooltool.py": "/tools/tooltool.py",
        "buildbot": "/tools/buildbot/bin/buildbot",
    },
    "manifest": {
        "upload_remote_host": "stage.mozilla.org",
        "upload_remote_basepath": "/pub/mozilla.org/b2g/manifests/nightly/%(version)s",
        "depend_upload_remote_basepath": "/pub/mozilla.org/b2g/manifests/depend/%(branch)s/%(platform)s/%(buildid)s",
        "ssh_key": os.path.expanduser("~/.ssh/b2gbld_dsa"),
        "ssh_user": "b2gbld",
        "branches": {
            'mozilla-b2g28_v1_3t': '1.3.0t',
            'mozilla-b2g30_v1_4': '1.4.0',
            'mozilla-b2g32_v2_0': '2.0.0',
            'mozilla-b2g34_v2_1': '2.1.0',
            'mozilla-central': '2.2.0',
        },
        "translate_hg_to_git": True,
        "translate_base_url": "http://cruncher.build.mozilla.org/mapper/{project}/{vcs}/{rev}",
    },
    "env": {
        "CCACHE_DIR": "/builds/ccache",
        "CCACHE_COMPRESS": "1",
        "CCACHE_UMASK": "002",
        "GAIA_OPTIMIZE": "1",
        "SYMBOL_SERVER_HOST": "symbolpush.mozilla.org",
        "SYMBOL_SERVER_USER": "b2gbld",
        "SYMBOL_SERVER_SSH_KEY": "/home/mock_mozilla/.ssh/b2gbld_dsa",
        "SYMBOL_SERVER_PATH": "/mnt/netapp/breakpad/symbols_b2g/",
        "POST_SYMBOL_UPLOAD_CMD": "/usr/local/bin/post-symbol-upload.py",
        "WGET_OPTS": "-c -q",
        "PATH": "/tools/python27/bin:%(PATH)s",
    },
    "purge_minsize": 20,
    "clobberer_url": "https://api.pub.build.mozilla.org/clobberer/lastclobber",
    "is_automation": True,
    "repo_mirror_dir": "/builds/git-shared/repo",
    "repo_remote_mappings": {
        'https://android.googlesource.com/': 'https://git.mozilla.org/external/aosp',
        'git://codeaurora.org/': 'https://git.mozilla.org/external/caf',
        'https://git.mozilla.org/b2g': 'https://git.mozilla.org/b2g',
        'git://github.com/mozilla-b2g/': 'https://git.mozilla.org/b2g',
        'git://github.com/mozilla/': 'https://git.mozilla.org/b2g',
        'https://git.mozilla.org/releases': 'https://git.mozilla.org/releases',
        'http://android.git.linaro.org/git-ro/': 'https://git.mozilla.org/external/linaro',
        'git://github.com/apitrace/': 'https://git.mozilla.org/external/apitrace',
    },
}
