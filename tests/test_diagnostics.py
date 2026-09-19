import unittest
from unittest.mock import MagicMock
import requests
from campusconnect.diagnostics import error_category, measured_get, reply_metadata


class DiagnosticsTests(unittest.TestCase):
    def test_exception_url_and_password_are_not_logged(self):
        session = MagicMock()
        session.get.side_effect = requests.exceptions.SSLError(
            'CERTIFICATE_VERIFY_FAILED http://test/?upass=PRIVATE_PASSWORD&DDDDD=PRIVATE_ACCOUNT')
        with self.assertLogs(level='INFO') as logs:
            with self.assertRaises(requests.exceptions.SSLError):
                with measured_get(session, '校园网登录', 'http://test/?upass=PRIVATE_PASSWORD',
                                  timeout=(5, 10), allow_redirects=False):
                    pass
        output = '\n'.join(logs.output)
        self.assertIn('TLS 证书校验失败', output)
        self.assertIn('耗时=', output)
        self.assertNotIn('PRIVATE', output)
        self.assertNotIn('upass', output)

    def test_response_body_and_unknown_fields_are_not_logged(self):
        session = MagicMock()
        session.get.return_value.__enter__.return_value.status_code = 200
        with self.assertLogs(level='INFO') as logs:
            with self.assertRaises(ValueError):
                with measured_get(session, '认证状态', 'http://test', timeout=(5, 8)):
                    raise ValueError('PRIVATE_RESPONSE')
        self.assertIn('HTTP=200', '\n'.join(logs.output))
        self.assertNotIn('PRIVATE', '\n'.join(logs.output))
        self.assertEqual(reply_metadata({'msg': 'PRIVATE', 'PRIVATE_KEY': 'PRIVATE'}), '已识别字段=msg')

    def test_timeout_and_dns_categories(self):
        self.assertEqual(error_category(requests.exceptions.ReadTimeout('PRIVATE')), '读取响应超时')
        self.assertEqual(error_category(requests.exceptions.ConnectionError('getaddrinfo PRIVATE')), 'DNS 解析失败')


if __name__ == '__main__':
    unittest.main()
