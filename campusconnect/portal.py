"""安徽理工大学有线与 AUST_Student 门户参数；来源见 docs/usage.md。"""
import time
from urllib.parse import urlencode

OPERATORS = {'电信': '@aust', '移动': '@cmcc', '联通': '@unicom'}


def build_login_url(account, password, operator):
    account = account.strip()
    if not account or not password:
        raise ValueError('请填写账号和密码。')
    if operator not in OPERATORS:
        raise ValueError('请选择运营商。')
    if '@' in account:
        account, suffix = account.rsplit('@', 1)
        if '@' + suffix != OPERATORS[operator] or not account or '@' in account:
            raise ValueError('账号后缀与运营商不一致，请只填写学号。')
    return 'http://10.255.0.19/drcom/login?' + urlencode({
        'callback': 'dr1003', 'DDDDD': account + OPERATORS[operator],
        'upass': password, '0MKKey': '123456', 'R1': '0', 'R3': '0',
        'R6': '0', 'para': '00', 'v6ip': '', 'v': time.time_ns(),
    })
