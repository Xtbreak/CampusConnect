import queue
import tempfile
import threading
import subprocess
import unittest
from unittest.mock import MagicMock, patch
from campusconnect import network, core, connection_worker as worker


class WifiConnectTests(unittest.TestCase):
    def test_saved_profile_and_interface(self):
        with patch.object(network.os, 'name', 'nt'), patch.object(network, 'command') as command:
            self.assertTrue(network.connect_campus_wifi(network.Network(interface='Wi-Fi 2', kind='wifi', ssid='Home')))
            command.assert_called_once_with(['netsh.exe', 'wlan', 'connect',
                                             'name=AUST_Student', 'ssid=AUST_Student', 'interface=Wi-Fi 2'])

    def test_no_switch_on_wired_campus_or_unknown(self):
        with patch.object(network.os, 'name', 'nt'), patch.object(network, 'command') as command:
            for current in (network.Network(kind='wired'), network.Network(),
                            network.Network(kind='wifi', ssid='AUST_Student')):
                self.assertFalse(network.connect_campus_wifi(current))
            command.assert_not_called()

    def test_missing_profile_or_disabled_adapter(self):
        with patch.object(network.os, 'name', 'nt'), \
             patch.object(network, 'command', side_effect=subprocess.CalledProcessError(1, 'netsh')):
            self.assertFalse(network.connect_campus_wifi(network.Network(kind='offline')))

    def test_option_off_never_connects(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(worker, 'snapshot', return_value=network.Network(kind='offline')), \
             patch.object(worker, 'connect_campus_wifi') as connect:
            worker.run_connections(('test', 'secret', '电信'), False, folder, queue.Queue(), threading.Event())
            connect.assert_not_called()

    def test_connect_before_authentication(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(worker, 'snapshot', side_effect=[network.Network(kind='offline'),
                                                          network.Network(kind='wifi', ssid='AUST_Student')]), \
             patch.object(worker, 'connect_campus_wifi', return_value=True) as connect, \
             patch.object(core, 'cycle', return_value=True) as cycle, \
             patch.object(core, 'connected', return_value=True):
            stop = MagicMock()
            stop.is_set.return_value = False
            stop.wait.return_value = False
            worker.run_connections(('test', 'secret', '电信'), False, folder, queue.Queue(), stop, True)
            connect.assert_called_once()
            cycle.assert_called_once()

    def test_stop_during_association_prevents_auth(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(worker, 'snapshot', return_value=network.Network(kind='offline')), \
             patch.object(worker, 'connect_campus_wifi', return_value=True), \
             patch.object(core, 'cycle') as cycle:
            stop = threading.Event()
            with patch.object(stop, 'wait', side_effect=lambda _: (stop.set() or True)):
                worker.run_connections(('test', 'secret', '电信'), False, folder, queue.Queue(), stop, True)
            cycle.assert_not_called()
