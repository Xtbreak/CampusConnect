import unittest
from urllib.parse import urlsplit, parse_qs
from portal import build_login_url


class LoginParametersTest(unittest.TestCase):
    def test_operator_and_password_roundtrip(self):
        for operator, suffix in [('电信', '@aust'), ('移动', '@cmcc'), ('联通', '@unicom')]:
            with self.subTest(operator=operator):
                password = ' space+&=?%中文@ '
                query = parse_qs(urlsplit(build_login_url('123', password, operator)).query)
                self.assertEqual(query['DDDDD'], ['123' + suffix])
                self.assertEqual(query['upass'], [password])
                self.assertEqual(query['R3'], ['0'])

    def test_existing_suffix_not_duplicated(self):
        query = parse_qs(urlsplit(build_login_url('123@cmcc', 'pw', '移动')).query)
        self.assertEqual(query['DDDDD'], ['123@cmcc'])

    def test_invalid_input_does_not_generate_request(self):
        for args in [('', 'pw', '电信'), ('123', '', '电信'), ('123', 'pw', ''),
                     ('123@aust', 'pw', '联通'), ('@aust', 'pw', '电信')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                build_login_url(*args)


if __name__ == '__main__':
    unittest.main()
