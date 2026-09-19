import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from campusconnect import core
from campusconnect import connection_worker as worker


def blocked_worker(credentials, auto, data_dir, events, stop):
    def blocked_cycle(*args, **kwargs):
        events.put(('ready', ''))
        time.sleep(60)  # Simulates a socket/DNS operation ignoring cancellation.
        (Path(data_dir) / 'unexpected-request').touch()
        return False
    with patch.object(core, 'cycle', side_effect=blocked_cycle):
        worker.run_connections(credentials, auto, data_dir, events, stop)


class CancellationTests(unittest.TestCase):
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
