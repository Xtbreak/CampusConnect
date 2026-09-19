import unittest
from unittest.mock import MagicMock, patch
import requests
from campusconnect import core


class AuthOnlyTests(unittest.TestCase):
    def run_case(self, replies, expected, expected_paths):
        session = MagicMock()
        responses = []
        for reply in replies:
            if isinstance(reply, Exception):
                responses.append(reply)
                continue
            response = MagicMock()
            response.__enter__.return_value = response
            response.text = reply
            response.status_code = 200
            responses.append(response)
        session.get.side_effect = responses
        with patch.object(core, 'connected') as external, patch.object(core.time, 'sleep') as sleep:
            result = core.cycle(session, 'http://test/drcom/login?upass=secret', True,
                                verify_internet=False)
            self.assertEqual(result, expected)
            external.assert_not_called()
        from urllib.parse import urlsplit
        self.assertEqual([urlsplit(c.args[0]).path for c in session.get.call_args_list], expected_paths)
        return sleep

    def test_online_only_queries_status(self):
        self.run_case(['{"result":1}'], True, ['/drcom/chkstatus']).assert_not_called()

    def test_offline_logs_in_and_immediately_verifies(self):
        self.run_case(['{"result":0}', '{"result":1}', '{"result":1}'], True,
                      ['/drcom/chkstatus', '/drcom/login', '/drcom/chkstatus']).assert_not_called()

    def test_unknown_does_not_login(self):
        self.run_case([requests.exceptions.ConnectTimeout()], False, ['/drcom/chkstatus'])

    def test_rejection_does_not_retry_immediately(self):
        self.run_case(['{"result":0}', '{"result":0}'], False,
                      ['/drcom/chkstatus', '/drcom/login']).assert_not_called()

    def test_login_success_requires_online_confirmation(self):
        sleep = self.run_case(['{"result":0}', '{"result":1}'] + ['{"result":0}'] * 3,
                             False, ['/drcom/chkstatus', '/drcom/login'] + ['/drcom/chkstatus'] * 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])


if __name__ == '__main__':
    unittest.main()
