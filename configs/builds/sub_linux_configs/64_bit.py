#### architecture differences ####

# if platform.architecture()[0] == '64bit':
# ENV.update({
#     'MOZ_SYMBOLS_EXTRA_BUILDID': 'linux64',
#     'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:/\
# usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:/\
# tools/python27-mercurial/bin:/home/cltbld/bin'
    # 'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib64",
# })
# ARCH_MOCK_PACKAGES = [
#     'glibc-static', 'libstdc++-static',
#     'gtk2-devel', 'libnotify-devel',
#     'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
#     'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
#     'GConf2-devel',
#     ### from releng repo
#     'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
#     'yasm', 'ccache',
#     ###
#     'pulseaudio-libs-devel', 'gstreamer-devel',
#     'gstreamer-plugins-base-devel', 'freetype-2.3.11-6.el6_1.8.x86_64',
#     'freetype-devel-2.3.11-6.el6_1.8.x86_64'
# ]
#####

    # 'packageFilename': '*.linux-x86_64*.tar.bz2',
    # "check_test_env": {
    #     'MINIDUMP_STACKWALK': 'breakpad/linux64/minidump_stackwalk',
    #     'MINIDUMP_SAVE_PATH': 'minidumps',
    # },
