import queue
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from campusconnect import core, network, connection_worker as worker


class NetworkTests(unittest.TestCase):
    def test_selected_mode_blocks_wrong_interface(self):
        for mode, current in [('wired', network.Network(kind='wifi', ssid='AUST_Student')),
                              ('wifi', network.Network(kind='wired'))]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder, \
                 patch.object(worker, 'snapshot', return_value=current), \
                 patch.object(worker, 'connect_campus_wifi') as connect, \
                 patch.object(core, 'cycle') as cycle, patch.object(core, 'connected') as probe:
                worker.run_connections(('test', 'secret', '电信'), False, folder,
                                       queue.Queue(), threading.Event(), mode == 'wifi', mode)
                cycle.assert_not_called()
                probe.assert_not_called()
                connect.assert_not_called()

    def test_mode_accepts_only_selected_interface(self):
        self.assertTrue(worker.mode_allows(network.Network(kind='wired'), 'wired'))
        self.assertTrue(worker.mode_allows(network.Network(kind='wifi', ssid='AUST_Student'), 'wifi'))
        self.assertFalse(worker.mode_allows(network.Network(kind='wifi', ssid='Home'), 'wifi'))

    def test_wifi_allowlist_is_exact_and_unknown_fails_closed(self):
        for ssid in ('Home', 'AUST_Student_fake', 'aust_student', ''):
            self.assertFalse(network.Network(kind='wifi', ssid=ssid).allowed)
        self.assertTrue(network.Network(kind='wifi', ssid='AUST_Student').allowed)
        self.assertTrue(network.Network(kind='wired').allowed)
        self.assertFalse(network.Network().allowed)

    def test_localized_multiple_adapters_and_bssid(self):
        output = ('    名称 : Wi-Fi 2\n    SSID : Home\n\n'
                  '    名称 : Wi-Fi\n    BSSID : aa:bb:cc:dd:ee:ff\n'
                  '    SSID : AUST_Student\n')
        self.assertEqual(network.wifi_ssid(output, 'Wi-Fi'), 'AUST_Student')
        self.assertEqual(network.wifi_ssid(output, 'Wi-Fi 2'), 'Home')
        self.assertEqual(network.wifi_ssid(output, 'Wi-Fi 3'), '')
        self.assertEqual(network.wifi_ssid('名称 : Wi-Fi\n BSSID : aa:bb', 'Wi-Fi'), '')

    def test_blocked_network_never_calls_portal_or_external_probe(self):
        for current in (network.Network(kind='offline'), network.Network(),
                        network.Network(kind='wifi', ssid='Home')):
            with self.subTest(current=current), tempfile.TemporaryDirectory() as folder, \
                 patch.object(worker, 'snapshot', return_value=current), \
                 patch.object(core, 'cycle') as cycle, patch.object(core, 'connected') as probe:
                events = queue.Queue()
                worker.run_connections(('test', 'secret', '电信'), False, folder, events, threading.Event())
                cycle.assert_not_called()
                probe.assert_not_called()
                states = [value for kind, value in list(events.queue) if kind == 'state']
                self.assertEqual(states, [current.message])

    def test_wifi_becomes_ready_and_auto_connects(self):
        wifi = network.Network(kind='wifi', ssid='AUST_Student')
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(worker, 'snapshot', side_effect=[network.Network(kind='offline'), wifi]), \
             patch.object(worker, 'wait_for_next_check', side_effect=[True, False]), \
             patch.object(core, 'cycle', return_value=True) as cycle, \
             patch.object(core, 'connected', return_value=True):
            worker.run_connections(('test', 'secret', '电信'), True, folder, queue.Queue(), threading.Event())
            cycle.assert_called_once()

    def test_changed_network_wakes_backoff(self):
        stop = threading.Event()
        with patch.object(worker.time, 'monotonic', side_effect=[0, 0, 0, 6]), \
             patch.object(worker, 'snapshot', return_value=network.Network(kind='wifi', ssid='AUST_Student')):
            self.assertTrue(worker.wait_for_next_check(stop, True, 1800, network.Network(kind='offline')))

    def test_guard_blocks_login_after_network_switch(self):
        session = MagicMock()
        with patch.object(core, 'status', return_value=(False, {})):
            self.assertFalse(core.cycle(session, 'http://test/drcom/login', True,
                                        verify_internet=False, login_guard=lambda: False))
        session.get.assert_not_called()

    def test_windows_probe_failure_fails_closed(self):
        with patch.object(network.os, 'name', 'nt'), patch.object(network.socket, 'socket') as sock, \
             patch.object(network, 'command', side_effect=OSError):
            sock.return_value.__enter__.return_value.getsockname.return_value = ('10.4.1.2', 0)
            self.assertFalse(network.snapshot().allowed)


if __name__ == '__main__':
    unittest.main()
