#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic ways to upload + download files.
"""

from mozharness.base.errors import SSHErrorList
from mozharness.base.log import ERROR

# TransferMixin {{{1
class TransferMixin(object):
    """
    Generic transfer methods.

    Dependent on BaseScript.
    """
    def upload_directory(self, local_path, remote_path,
                         ssh_key, ssh_user, remote_host,
                         rsync_options=None,
                         error_level=ERROR,
                         create_remote_directory=True,
                        ):
        """
        Create a remote directory and upload the contents of
        a local directory to it via rsync+ssh.

        Return None on success, not None on failure.
        """
        c = self.config
        dirs = self.query_abs_dirs()
        self.info("Uploading the contents of %s to %s:%s." % (local_path, remote_host, remote_path))
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        if rsync_options is None:
            rsync_options = ['-azv']
        if not os.path.isdir(local_path):
            self.log("%s isn't a directory!" % local_path,
                     level=error_level)
            return -1
        if create_remote_directory:
            if self.run_command([ssh, '-oIdentityFile=%s' % ssh_key,
                                 '%s@%s' % (ssh_user, remote_host),
                                 'mkdir', '-p', remote_path],
                                cwd=dirs['abs_work_dir'],
                                return_type='num_errors',
                                error_list=SSHErrorList):
                self.log("Unable to create remote directory %s@%s:%s!" % (remote_host, remote_path),
                         level=error_level)
                return -2
        if self.run_command([rsync, '-e',
                             '%s -oIdentityFile=%s' % (ssh, ssh_key)
                            ] + rsync_options + ['.',
                             '%s@%s:%s/' % (ssh_user, remote_host, remote_path)],
                            cwd=local_path,
                            return_type='num_errors',
                            error_list=SSHErrorList):
            self.log("Unable to rsync %s to %s:%s!" % (local_path, remote_host, remote_path),
                     level=error_level)
            return -3
