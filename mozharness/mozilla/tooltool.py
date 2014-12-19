"""module for tooltool operations"""
import os

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import ERROR, FATAL
from mozharness.mozilla.proxxy import Proxxy

TooltoolErrorList = PythonErrorList + [{
    'substr': 'ERROR - ', 'level': ERROR
}]


class TooltoolMixin(object):
    """Mixin class for handling tooltool manifests.
    Requires self.config['tooltool_servers'] to be a list of base urls
    """
    def tooltool_fetch(self, manifest, bootstrap_cmd=None,
                       output_dir=None, privileged=False, cache=None):
        """docstring for tooltool_fetch"""
        tooltool = self.query_exe('tooltool.py', return_type='list')
        cmd = tooltool
        # get the tooltools servers from configuration
        default_urls = self.config['tooltool_servers']
        proxxy = Proxxy(self.config, self.log_obj)
        proxxy_urls = proxxy.get_proxies_and_urls(default_urls)

        for proxyied_url in proxxy_urls:
            cmd.extend(['--url', proxyied_url])

        cmd.extend(['fetch', '-m', manifest, '-o'])

        if cache:
            cmd.extend(['-c', cache])

        self.retry(
            self.run_command,
            args=(cmd, ),
            kwargs={'cwd': output_dir,
                    'error_list': TooltoolErrorList,
                    'privileged': privileged,
                    },
            good_statuses=(0, ),
            error_message="Tooltool %s fetch failed!" % manifest,
            error_level=FATAL,
        )
        if bootstrap_cmd is not None:
            error_message = "Tooltool bootstrap %s failed!" % str(bootstrap_cmd)
            self.retry(
                self.run_command,
                args=(bootstrap_cmd, ),
                kwargs={'cwd': output_dir,
                        'error_list': TooltoolErrorList,
                        'privileged': privileged,
                        },
                good_statuses=(0, ),
                error_message=error_message,
                error_level=FATAL,
            )

    def create_tooltool_manifest(self, contents, path=None):
        """ Currently just creates a manifest, given the contents.
        We may want a template and individual values in the future?
        """
        if path is None:
            dirs = self.query_abs_dirs()
            path = os.path.join(dirs['abs_work_dir'], 'tooltool.tt')
        self.write_to_file(path, contents, error_level=FATAL)
        return path
