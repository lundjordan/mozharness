STAGE_PRODUCT = 'firefox'
# TODO Reminder, stage_username and stage_ssh_key differ on Try
STAGE_USERNAME = 'ffxbld'
STAGE_SSH_KEY = 'ffxbld_dsa'

config = {
    #########################################################################
    ######## WINDOWS GENERIC CONFIG KEYS/VAlUES
    # if you are updating this with custom 32 bit keys/values please add them
    # below under the '32 bit specific' code block otherwise, update in this
    # code block and also make sure this is synced with
    # releng_base_linux_64_builds.py

#     'periodic_clobber': 168,  # default anyway but can be overwritten
#
#     'app_ini_path': '%(obj_dir)s/dist/bin/application.ini',
#     # decides whether we want to use moz_sign_cmd in env
#     'enable_signing': True,
#     "buildbot_json_path": "buildprops.json",
    'default_actions': [
        'clobber',
        'clone-tools',
        'setup-mock',
        'build',
        'generate-build-props',
        # 'generate-build-stats',
        'symbols',
        'packages',
        'upload',
        'sendchanges',
        'pretty-names',
        'check-l10n',
        'check-test',
        'update',  # decided by query_is_nightly()
        'enable-ccache',
    ],
    'exes': {
        "buildbot": "/tools/buildbot/bin/buildbot",
        "make": ["python", "%(abs_work_dir)s/source/build/pymake/make.py"]
    },
#     'purge_skip': ['info', 'rel-*:45d', 'tb-rel-*:45d'],
#     'purge_basedirs':  ["/mock/users/cltbld/home/cltbld/build"],
    'enable_ccache': False,
#     'vcs_share_base': '/builds/hg-shared',
#     'objdir': 'obj-firefox',
#     'old_packages': [
#         "%(objdir)s/dist/firefox-*",
#         "%(objdir)s/dist/fennec*",
#         "%(objdir)s/dist/seamonkey*",
#         "%(objdir)s/dist/thunderbird*",
#         "%(objdir)s/dist/install/sea/*.exe"
#     ],
    'tooltool_script': ['python', '/c/mozilla-build/tooltool.py'],
    'tooltool_bootstrap': "setup.sh",
    # only linux counts ctors
    'enable_count_ctors': False,
#     'enable_package_tests': True,
#     'stage_product': STAGE_PRODUCT,
#     "enable_talos_sendchange": True,
#     "do_pretty_name_l10n_check": True,
#     'upload_symbols': True,
#
#     'stage_username': STAGE_USERNAME,
#     'stage_ssh_key': STAGE_SSH_KEY,
#     'upload_env': {
#         # stage_server is dictated from build_pool_specifics.py
#         'UPLOAD_HOST': "%(stage_server)s",
#         'UPLOAD_USER': STAGE_USERNAME,
#         'UPLOAD_TO_TEMP': '1',
#         'UPLOAD_SSH_KEY': '~/.ssh/%s' % (STAGE_SSH_KEY,),
#         },
#     'update_env': {
#         'MAR': '../dist/host/bin/mar',
#         'MBSDIFF': '../dist/host/bin/mbsdiff'
#     },
#     'latest_mar_dir': '/pub/mozilla.org/%s/nightly/latest-%%(branch)s' % (
#         STAGE_PRODUCT,),
#     #########################################################################
#
#
#     #########################################################################
#     ###### 32 bit specific ######
#     'platform': 'linux',
#     'stage_platform': 'linux',
#     'platform_ftp_name': 'linux-i686.complete.mar',
    'enable_installer': True,
    'env': {
        'BINSCOPE': 'C:\\Program Files (x86)\\Microsoft\\SDL BinScope\\BinScope.exe',
        'HG_SHARE_BASE_DIR': 'c:/builds/hg-shared',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'MOZ_OBJDIR': 'obj-firefox',
        'PATH': '${MOZILLABUILD}nsis-2.46u;${MOZILLABUILD}python27;${MOZILLABUILD}buildbotve\\scripts;${PATH}',
        'PDBSTR_PATH': '/c/Program Files (x86)/Windows Kits/8.0/Debuggers/x64/srcsrv/pdbstr.exe',
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'SYMBOL_SERVER_HOST': 'symbolpush.mozilla.org',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'SYMBOL_SERVER_SSH_KEY': '/c/Users/cltbld/.ssh/ffxbld_dsa',
        'SYMBOL_SERVER_USER': 'ffxbld',
        'TINDERBOX_OUTPUT': '1'
    },
#     'purge_minsize': 12,
#     'mock_packages': [
#         'autoconf213', 'python', 'zip', 'mozilla-python27-mercurial',
#         'git', 'ccache', 'perl-Test-Simple', 'perl-Config-General',
#         'yasm', 'wget',
#         'mpfr',  # required for system compiler
#         'xorg-x11-font*',  # fonts required for PGO
#         'imake',  # required for makedepend!?!
#         ### <-- from releng repo
#         'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
#         'yasm', 'ccache',
#         ###
#         'valgrind',
#         ######## 32 bit specific ###########
#         'glibc-static.i686', 'libstdc++-static.i686',
#         'gtk2-devel.i686', 'libnotify-devel.i686',
#         'alsa-lib-devel.i686', 'libcurl-devel.i686',
#         'wireless-tools-devel.i686', 'libX11-devel.i686',
#         'libXt-devel.i686', 'mesa-libGL-devel.i686',
#         'gnome-vfs2-devel.i686', 'GConf2-devel.i686',
#         'pulseaudio-libs-devel.i686',
#         'gstreamer-devel.i686', 'gstreamer-plugins-base-devel.i686',
#         # Packages already installed in the mock environment, as x86_64
#         # packages.
#         'glibc-devel.i686', 'libgcc.i686', 'libstdc++-devel.i686',
#         # yum likes to install .x86_64 -devel packages that satisfy .i686
#         # -devel packages dependencies. So manually install the dependencies
#         # of the above packages.
#         'ORBit2-devel.i686', 'atk-devel.i686', 'cairo-devel.i686',
#         'check-devel.i686', 'dbus-devel.i686', 'dbus-glib-devel.i686',
#         'fontconfig-devel.i686', 'glib2-devel.i686',
#         'hal-devel.i686', 'libICE-devel.i686', 'libIDL-devel.i686',
#         'libSM-devel.i686', 'libXau-devel.i686', 'libXcomposite-devel.i686',
#         'libXcursor-devel.i686', 'libXdamage-devel.i686',
#         'libXdmcp-devel.i686', 'libXext-devel.i686', 'libXfixes-devel.i686',
#         'libXft-devel.i686', 'libXi-devel.i686', 'libXinerama-devel.i686',
#         'libXrandr-devel.i686', 'libXrender-devel.i686',
#         'libXxf86vm-devel.i686', 'libdrm-devel.i686', 'libidn-devel.i686',
#         'libpng-devel.i686', 'libxcb-devel.i686', 'libxml2-devel.i686',
#         'pango-devel.i686', 'perl-devel.i686', 'pixman-devel.i686',
#         'zlib-devel.i686',
#         # Freetype packages need to be installed be version, because a newer
#         # version is available, but we don't want it for Firefox builds.
#         'freetype-2.3.11-6.el6_1.8.i686',
#         'freetype-devel-2.3.11-6.el6_1.8.i686',
#         'freetype-2.3.11-6.el6_1.8.x86_64',
#         ######## 32 bit specific ###########
#     ],
    'src_mozconfig': 'browser/config/mozconfigs/win32/nightly',
    'tooltool_manifest_src': "browser/config/tooltool-manifests/win32/releng.manifest",
    'package_filename': '*.win32.zip',
#
#     "check_test_env": {
#         'MINIDUMP_STACKWALK': 'breakpad/linux/minidump_stackwalk',
#         'MINIDUMP_SAVE_PATH': 'minidumps',
#         },
#     'base_name': 'Linux_%(branch)s',
#     'update_platform': 'Linux_x86-gcc3',
    #########################################################################
}
