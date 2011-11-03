#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Mike Taylor <bear@mozilla.com>
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
'''Interact with a device via ADB or SUT.

This code is largely from
http://hg.mozilla.org/build/tools/file/default/sut_tools
'''

import os
import re
import signal
import socket
import subprocess
import sys
import time

from mozharness.base.errors import PythonErrorList, BaseErrorList, ADBErrorList
from mozharness.base.log import LogMixin, DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE
from mozharness.base.script import ShellMixin, OSMixin



class DeviceException(Exception):
    pass



# BaseDeviceHandler {{{1
class BaseDeviceHandler(ShellMixin, OSMixin, LogMixin):
    device_id = None
    def __init__(self, log_obj=None, config=None):
        super(BaseDeviceHandler, self).__init__()
        self.log_obj = log_obj
        self.config = config

    def query_device_id(self):
        if self.device_id:
            return self.device_id
        c = self.config
        device_id = None
        if c.get('device_id'):
            device_id = c['device_id']
        elif c.get('device_ip'):
            device_id = "%s:%s" % (c['device_ip'],
                                   c.get('device_port', self.default_port))
        self.device_id = device_id
        return self.device_id

    def exit_on_error(self, message, *args, **kwargs):
        '''When exit_on_error is defined, a FATAL log call will call it
        and use the message and other args from it.
        '''
        if self.config['enable_automation']:
            # TODO take device out of production if required?
            # TODO we might want a method flag for that.
            message = "Remote Device Error: %s" % message
        return (message, args, kwargs)

    def ping_device(self):
        pass

    def check_device(self):
        pass

    def query_device_root(self):
        pass



# ADBDeviceHandler {{{1
class ADBDeviceHandler(BaseDeviceHandler):
    def __init__(self, **kwargs):
        super(ADBDeviceHandler, self).__init__(**kwargs)
        self.default_port = 5555

    def query_device_exe(self, exe_name):
        return self.query_exe(exe_name, exe_dict="device_exes")

    def query_device_id(self, auto_connect=True):
        if self.device_id:
            return self.device_id
        c = self.config
        device_id = self._query_config_device_id()
        if device_id:
            if auto_connect:
                self.ping_device(auto_connect=True)
        else:
            self.info("Trying to find device...")
            devices = self._query_attached_devices()
            if not devices:
                self.fatal("No device attached via adb!\nUse 'adb connect' or specify a device_id or device_ip in config!")
            elif len(devices) > 1:
                self.warning("""More than one device detected; specify 'device_id' or\n'device_ip' to target a specific device!""")
            device_id = devices[0]
            self.info("Found %s." % device_id)
        self.device_id = device_id
        return self.device_id

    # maintenance {{{2
    def ping_device(self, auto_connect=False, silent=False):
        c = self.config
        if auto_connect and not self._query_attached_devices():
            self.connect_device()
        if not silent:
            self.info("Determining device connectivity over adb...")
        serial = self.query_device_id()
        adb = self.query_exe('adb')
        uptime = self.query_device_exe('uptime')
        output = self.get_output_from_command([adb, "-s", serial,
                                               "shell", uptime],
                                              silent=silent)
        if str(output).startswith("up time:"):
            if not silent:
                self.info("Found %s." % serial)
            return True
        elif auto_connect:
            # TODO retry?
            self.connect_device()
            return self.ping_device()
        else:
            if not silent:
                self.error("Can't find a device.")
            return False

    def _query_attached_devices(self):
        devices = []
        adb = self.query_exe('adb')
        output = self.get_output_from_command([adb, "devices"])
        starting_list = False
        for line in output:
            if 'adb: command not found' in line:
                self.fatal("Can't find adb; install the Android SDK!")
            if line.startswith("* daemon"):
                continue
            if line.startswith("List of devices"):
                starting_list = True
                continue
            # TODO somehow otherwise determine whether this is an actual
            # device?
            if starting_list:
                devices.append(re.split('\s+', line)[0])
        return devices

    def connect_device(self):
        self.info("Connecting device...")
        adb = self.query_exe('adb')
        cmd = [adb, "connect"]
        device_id = self._query_config_device_id()
        if device_id:
            devices = self._query_attached_devices()
            if device_id in devices:
                # TODO is this the right behavior?
                self.disconnect_device()
            cmd.append(device_id)
        status = self.run_command(cmd, error_list=ADBErrorList)

    def disconnect_device(self):
        self.info("Disconnecting device...")
        device_id = self.query_device_id()
        if device_id:
            adb = self.query_exe('adb')
            status = self.run_command([adb, "-s", device_id,
                                       "disconnect"],
                                      error_list=ADBErrorList)
        else:
            self.info("No device found.")

    def check_device(self):
        if not self.ping_device(auto_connect=True):
            self.fatal("Can't find device!")
        if self.query_device_root() is None:
            self.fatal("Can't connect to device!")

    def reboot_device(self):
        if not self.ping_device(auto_connect=True):
            self.error("Can't reboot disconnected device!")
            return False
        device_id = self.query_device_id()
        self.info("Rebooting device...")
        adb = self.query_exe('adb')
        cmd = [adb, "-s", device_id, "reboot"]
        self.info("Running command (in the background): %s" % cmd)
        # This won't exit until much later, but we don't need to wait.
        # However, some error checking would be good.
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        time.sleep(10)
        self.disconnect_device()
        status = False
        try:
            self.wait_for_device()
            status = True
        except DeviceException:
            self.error("Can't reconnect to device!")
        return status

    def cleanup_device(self):
        self.info("Cleaning up device.")
        c = self.config
        device_id = self.query_device_id()
        status = self.remove_device_root()
        if not status:
            self.fatal("Can't remove device root!")
        if c.get("enable_automation"):
            self.remove_etc_hosts()
        if c.get("device_package_name"):
            adb = self.query_exe('adb')
            killall = self.query_device_exe('killall')
            self.run_command([adb, "-s", device_id, "shell",
                              killall, c["device_package_name"]],
                              error_list=ADBErrorList)
            self.uninstall_app(c['device_package_name'])

    # device calls {{{2
    def query_device_root(self, silent=False):
        if self.device_root:
            return self.device_root
        device_root = None
        device_id = self.query_device_id()
        adb = self.query_exe('adb')
        output = self.get_output_from_command("%s -s %s shell df" % (adb, device_id),
                                              silent=silent)
        # TODO this assumes we're connected; error checking?
        if "/mnt/sdcard" in output:
            device_root = "/mnt/sdcard/tests"
        elif ' not found' in output:
            self.error("Can't get output from 'adb shell df'!\n%s" % output)
            return None
        else:
            device_root = "/data/local/tmp/tests"
        if not silent:
            self.info("Device root is %s" % device_root)
        self.device_root = device_root
        return self.device_root

    # TODO from here on down needs to be copied to Base+SUT
    def wait_for_device(self, interval=60, max_attempts=20):
        self.info("Waiting for device to come back...")
        time.sleep(interval)
        tries = 0
        while tries <= max_attempts:
            tries += 1
            self.info("Try %d" % tries)
            if self.ping_device(auto_connect=True, silent=True):
                return self.ping_device()
            time.sleep(interval)
        raise DeviceException, "Remote Device Error: waiting for device timed out."

    def query_device_time(self):
        c = self.config
        serial = self.query_device_id()
        adb = self.query_exe('adb')
        # adb shell 'date' will give a date string
        date_string = self.get_output_from_command([adb, "-s", serial,
                                                    "shell", "date"])
        # TODO what to do when we error?
        return date_string

    def set_device_time(self, device_time=None, error_level='error'):
        # adb shell date UNIXTIMESTAMP will set date
        c = self.config
        serial = self.query_device_id()
        if device_time is None:
            device_time = time.time()
        self.info(self.query_device_time())
        adb = self.query_exe('adb')
        status = self.run_command([adb, "-s", serial,  "shell", "date",
                                   str(device_time)],
                                  error_list=ADBErrorList)
        self.info(self.query_device_time())
        return status

    def query_device_file_exists(self, file_name):
        device_id = self.query_device_id()
        adb = self.query_exe('adb')
        output = self.get_output_from_command([adb, "-s", device_id,
                                               "shell", "ls", "-d", file_name])
        if output.rstrip() == file_name:
            return True
        return False

    def remove_device_root(self, error_level='error'):
        device_root = self.query_device_root()
        device_id = self.query_device_id()
        if device_root is None:
            self.fatal("Can't connect to device!")
        adb = self.query_exe('adb')
        if self.query_device_file_exists(device_root):
            self.info("Removing device root %s." % device_root)
            self.run_command([adb, "-s", device_id, "shell", "rm",
                              "-r", device_root], error_list=ADBErrorList)
            if self.query_device_file_exists(device_root):
                self.log("Unable to remove device root!", level=error_level)
                return False
        return True

    def uninstall_app(self, package_name, package_root="/data/data",
                      error_level="error"):
        c = self.config
        device_id = self.query_device_id()
        self.info("Uninstalling %s..." % package_name)
        if self.query_device_file_exists('%s/%s' % (package_root, package_name)):
            adb = self.query_exe('adb')
            cmd = [adb, "-s", device_id, "uninstall"]
            if not c.get('enable_automation'):
                cmd.append("-k")
            cmd.append(package_name)
            status = self.run_command(cmd, error_list=ADBErrorList)
            # TODO is this the right error check?
            if status:
                self.log("Failed to uninstall %s!" % package_name,
                         level=error_level)

    # Device-type-specific. {{{2
    def remove_etc_hosts(self, hosts_file="/system/etc/hosts"):
        c = self.config
        if c['device_type'] not in ("tegra250",):
            self.debug("No need to remove /etc/hosts on a non-Tegra250.")
            return
        device_id = self.query_device_id()
        if self.query_device_file_exists(hosts_file):
            self.info("Removing %s file." % hosts_file)
            adb = self.query_exe('adb')
            self.run_command([adb, "-s", device_id, "shell",
                              "mount", "-o", "remount,rw", "-t", "yaffs2",
                              "/dev/block/mtdblock3", "/system"],
                             error_list=ADBErrorList)
            self.run_command([adb, "-s", device_id, "shell", "rm",
                              hosts_file])
            if self.query_device_file_exists(hosts_file):
                self.fatal("Unable to remove %s!" % hosts_file)
        else:
            self.debug("%s file doesn't exist; skipping." % hosts_file)



# SUTDeviceHandler {{{1
class SUTDeviceHandler(BaseDeviceHandler):
    def __init__(self, **kwargs):
        super(SUTDeviceHandler, self).__init__(**kwargs)
        self.devicemanager = None
        self.default_port = 20701

    def query_devicemanager(self):
        # TODO WRITEME
        pass

    # maintenance {{{2
    def ping_device(self):
        #TODO writeme
        pass

    def check_device(self):
        pass

    def reboot_device(self):
        pass

    def cleanup_device(self):
        pass

    # device calls {{{2
    def query_device_root(self):
        #TODO writeme
        pass

    # device type specific {{{2
    def remove_etc_hosts(self, hosts_file="/system/etc/hosts"):
        pass



# DeviceMixin {{{1
DEVICE_PROTOCOL_DICT = {
    'adb': ADBDeviceHandler,
    'sut': SUTDeviceHandler,
}

device_config_options = [[
 ["--device-ip"],
 {"action": "store",
  "dest": "device_ip",
  "help": "Specify the IP address of the device."
 }
],[
 ["--device-port"],
 {"action": "store",
  "dest": "device_port",
  "help": "Specify the IP port of the device."
 }
],[
 ["--device-protocol"],
 {"action": "choice",
  "dest": "device_protocol",
  "choices": DEVICE_PROTOCOL_DICT.keys(),
  "help": "Specify the device communication protocol."
 }
],[
 ["--device-type"],
 # A bit useless atm, but we can add new device types as we add support
 # for them.
 {"action": "store",
  "type": "choice",
  "choices": ["non-tegra", "tegra250"],
  "default": "non-tegra",
  "dest": "device_type",
  "help": "Specify the device type."
 }
]]

class DeviceMixin(object):
    '''BaseScript mixin, designed to interface with the device.

    '''
    device_handler = None
    device_root = None

    def query_device_handler(self):
        if self.device_handler:
            return self.device_handler
        c = self.config
        device_protocol = c.get('device_protocol')
        device_class = DEVICE_PROTOCOL_DICT.get(device_protocol)
        if not device_class:
            self.fatal("Unknown device_protocol %s; set via --device-protocol!" % str(device_protocol))
        self.device_handler = device_class(
         log_obj=self.log_obj,
         config=self.config
        )
        return self.device_handler



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
