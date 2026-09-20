import queue
import tempfile
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from campusconnect import core
from campusconnect import connection_worker as worker
from campusconnect.network import Network


def blocked_worker(credentials, auto, data_dir, events, stop, wifi_auto=False, mode='auto'):
    def blocked_cycle(*args, **kwargs):
        events.put(('ready', ''))
        time.sleep(60)  # Simulates a socket/DNS operation ignoring cancellation.
        (Path(data_dir) / 'unexpected-request').touch()
        return False
    with patch.object(core, 'cycle', side_effect=blocked_cycle), \
         patch.object(worker, 'snapshot', return_value=Network(kind='wired')):
        worker.run_connections(credentials, auto, data_dir, events, stop)


def online_worker(credentials, auto, data_dir, events, stop, wifi_auto=False, mode='auto'):
    with patch.object(core, 'cycle', return_value=True), \
         patch.object(worker, 'snapshot', return_value=Network(kind='wired')), \
         patch.object(core, 'connected', return_value=True):
        worker.run_connections(credentials, auto, data_dir, events, stop)


class CancellationTests(unittest.TestCase):
    def test_disable_auto_reaches_running_child_without_termination(self):
        with tempfile.TemporaryDirectory() as folder:
            task = worker.ConnectionTask()
            try:
                with patch.object(worker, 'run_connections', online_worker):
                    task.start(('test', 'test', '电信'), True, folder)
                deadline = time.monotonic() + 10
                while True:
                    kind, value = task.events.get(timeout=max(0.01, deadline - time.monotonic()))
                    if kind == 'state':
                        self.assertIn('自动检查中', value)
                        break
                task.set_auto(False)
                task.process.join(timeout=3)
                self.assertEqual(task.process.exitcode, 0)
                self.assertFalse(task.stopping)
                self.assertFalse(task.stop_event.is_set())
            finally:
                task.stop()
                if task.process is not None:
                    task.process.join(timeout=2)
                task.dispose()

    def test_saved_auto_setting_can_cancel_long_monitor_wait(self):
        auto = threading.Event()
        auto.set()
        stop = threading.Event()
        finished = threading.Event()
        results = []
        def wait():
            results.append(worker.wait_for_next_check(stop, auto, 1800))
            finished.set()
        thread = threading.Thread(target=wait, daemon=True)
        thread.start()
        auto.clear()
        try:
            self.assertTrue(finished.wait(2))
            self.assertEqual(results, [False])
            self.assertFalse(stop.is_set())
        finally:
            stop.set()
            thread.join(timeout=2)

    def test_desktop_status_follows_actual_internet_probe(self):
        for authenticated, internet in [(True, True), (True, False), (False, True), (False, False)]:
            with self.subTest(authenticated=authenticated, internet=internet), \
                 tempfile.TemporaryDirectory() as folder, \
                 patch.object(worker, 'snapshot', return_value=Network(kind='wired')), \
                 patch.object(core, 'cycle', return_value=authenticated) as cycle, \
                 patch.object(core, 'connected', return_value=internet) as probe:
                events = queue.Queue()
                stop = MagicMock()
                stop.is_set.return_value = False
                worker.run_connections(('test', 'test', '电信'), False, folder, events, stop)
                messages = []
                while not events.empty():
                    kind, value = events.get_nowait()
                    if kind == 'state':
                        messages.append(value)
                probe.assert_called_once()
                self.assertFalse(cycle.call_args.kwargs['verify_internet'])
                self.assertEqual(len(messages), 1)
                if internet:
                    self.assertEqual(messages[0], '网络已连接。')
                else:
                    self.assertIn('外网检测失败', messages[0])
                    self.assertIn('校园网已认证' if authenticated else '认证也未确认', messages[0])
                self.assertNotIn('未检测外网', messages[0])

    def test_second_connection_cannot_acquire_live_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'AutoConnect.lock'
            with core.OperationLock(path):
                with self.assertRaises(RuntimeError):
                    with core.OperationLock(path):
                        self.fail('A second task acquired the active lock')
            with core.OperationLock(path):
                pass

    def test_stop_interrupts_blocked_work_and_releases_lock_for_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            task = worker.ConnectionTask()
            try:
                for _ in range(2):
                    with patch.object(worker, 'run_connections', blocked_worker):
                        task.start(('test', 'test', '电信'), True, folder)
                    deadline = time.monotonic() + 10
                    while True:
                        kind, _ = task.events.get(timeout=max(0.01, deadline - time.monotonic()))
                        if kind == 'ready':
                            break
                    self.assertEqual(kind, 'ready')
                    started = time.monotonic()
                    task.stop()
                    task.process.join(timeout=2)
                    self.assertFalse(task.is_alive())
                    self.assertLess(time.monotonic() - started, 2)
                    with core.OperationLock(Path(folder) / 'AutoConnect.lock'):
                        pass
                    task.dispose()
                self.assertFalse((Path(folder) / 'unexpected-request').exists())
            finally:
                task.stop()
                if task.process is not None:
                    task.process.join(timeout=2)
                task.dispose()

    def test_diagnostics_do_not_echo_credentials(self):
        message = core.login_failure_summary({'result': 0, 'msga': 'password wrong SECRET',
                                             'ret_code': '1', 'msg': 'http://server/?upass=SECRET'})
        self.assertIn('result=0', message)
        self.assertIn('ret_code=1', message)
        self.assertNotIn('SECRET', message)
        self.assertNotIn('http', message)

    def test_explicit_rejection_skips_followup_probes(self):
        from unittest.mock import MagicMock
        session = MagicMock()
        session.get.return_value.__enter__.return_value.text = '{"result":0,"ret_code":1}'
        with patch.object(core, 'connected') as connected, patch.object(core.time, 'sleep') as sleep:
            self.assertFalse(core.cycle(session, 'http://test/drcom/login', True, force_login=True))
            connected.assert_not_called()
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
