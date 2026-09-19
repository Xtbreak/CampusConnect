"""校园网自动恢复：定期检查、确认离线、认证后检查外网。"""
import argparse
import ast
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import ipaddress
import logging
import builtins
import os
import msvcrt
from logging.handlers import TimedRotatingFileHandler

import requests
from diagnostics import measured_get, reply_metadata

# 仅保留兼容旧版脚本的占位变量；真实账号和 Token 存放在被 .gitignore 忽略的
# credentials.json 中，由 config.json 的模板在运行时拼接。
login_url = 'http://10.255.0.19/drcom/login?callback=dr1003&DDDDD=YOUR_ACCOUNT&upass=YOUR_TOKEN&0MKKey=123456&R1=0&R3=0&R6=0&para=00&v6ip=&v=8187'

VERSION = '2026-09-19.2'


def print(*args, **kwargs):
    # 只记录程序自身构造的信息，不记录认证 URL、响应正文或异常正文。
    logging.info(' '.join(str(arg) for arg in args))


class OperationLock:
    """Windows 文件锁在进程退出时自动释放，锁文件保留不代表仍被占用。"""
    def __init__(self, path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.handle = open(self.path, 'a+b')
        self.handle.seek(0, 2)
        if self.handle.tell() == 0:
            self.handle.write(b'0')
            self.handle.flush()
        self.handle.seek(0)
        try:
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.handle.close()
            self.handle = None
            raise RuntimeError('已有实例正在运行')
        return self

    def __exit__(self, *args):
        if self.handle:
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.handle.close()


CHECK_URLS = ('https://www.baidu.com/', 'https://www.qq.com/', 'https://www.bing.com/')


def load_login_url(path):
    """Load a login URL from the legacy Python file or the new local JSON config."""
    path = Path(path)
    if path.suffix.lower() == '.json':
        config = json.loads(path.read_text(encoding='utf-8-sig'))
        template = str(config.get('login_url_template', '')).strip()
        if not template:
            raise ValueError('配置缺少 login_url_template')
        credential_path = path.parent / str(config.get('credentials_file', 'credentials.json'))
        if not credential_path.exists():
            raise ValueError('未找到本地凭据文件，请先运行 setup.py')
        credentials = json.loads(credential_path.read_text(encoding='utf-8-sig'))
        account = str(credentials.get('account', '')).strip()
        token = str(credentials.get('token', '')).strip()
        if not account or not token:
            raise ValueError('本地凭据缺少 account 或 token')
        # URL 模板必须使用 urlencode 友好的占位符，避免特殊字符破坏请求。
        from urllib.parse import quote
        values = {'account': quote(account, safe=''), 'token': quote(token, safe='')}
        return template.format(**values)
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == 'login_url' for t in node.targets):
                value = ast.literal_eval(node.value)
                if isinstance(value, str) and urlsplit(value).hostname:
                    return value
    raise ValueError('原脚本没有可读取的 login_url 字符串')


def connected(session):
    passed = False
    for url in CHECK_URLS:
        try:
            with measured_get(session, '外网检测 ' + str(urlsplit(url).hostname), url,
                              timeout=(5, 8), allow_redirects=False, stream=True) as response:
                print(f'外网检测 {urlsplit(url).hostname}: HTTP {response.status_code}')
                if response.status_code == 200:
                    return True
        except requests.RequestException as exc:
            print(f'外网检测 {urlsplit(url).hostname}: {type(exc).__name__}')
    return passed


def parse_reply(text):
    text = text.strip().lstrip('\ufeff')
    match = re.fullmatch(r'[\w.$]+\s*\((.*)\)\s*;?', text, re.S)
    value = json.loads(match.group(1) if match else text)
    if not isinstance(value, dict):
        raise ValueError('认证响应不是对象')
    return value


def status(session, login_url):
    parts = urlsplit(login_url)
    try:
        with measured_get(session, '认证状态 /drcom/chkstatus',
                         f'{parts.scheme}://{parts.netloc}/drcom/chkstatus',
                         params={'callback': 'dr1001', 'v': time.time_ns()},
                         timeout=(5, 8), allow_redirects=False) as response:
            response.raise_for_status()
            data = parse_reply(response.text)
            print('[状态响应] ' + reply_metadata(data))
        state = str(data.get('result'))
        if state not in ('0', '1'):
            raise ValueError('未知状态')
        print('认证状态：' + ('在线' if state == '1' else '离线'))
        return state == '1', data
    except (requests.RequestException, ValueError) as exc:
        print(f'认证状态：未知（{type(exc).__name__}）')
        return None, {}


def cycle(session, login_url, permit_login, force_login=False, verify_internet=True):
    print(f'[连接检查] 允许登录={permit_login}；强制登录={force_login}；外网检测={verify_internet}')
    if not force_login:
        online, _ = status(session, login_url)
        if not verify_internet:
            print(f'[检查结果] 认证在线={online}；未检测外网')
            if online is True:
                print('已确认认证在线；未验证外网可用性。')
                return True
        internet = connected(session) if verify_internet else False
        if verify_internet:
            print(f'[检查结果] 认证在线={online}；外网可用={internet}')
        if online is True and internet:
            print('检查通过：认证在线，且至少一个外网检测地址可访问。')
            return True
        if not permit_login:
            return False
        if internet:
            print('外网可用但认证状态不一致，暂不改变当前连接。')
            return True
        if online is None:
            print('认证服务器状态未知，本轮不发送登录或注销请求。')
            return False
    print('发送登录请求……')
    try:
        with measured_get(session, '校园网登录 /drcom/login', login_url,
                          timeout=(5, 10), allow_redirects=False) as response:
            response.raise_for_status()
            reply = parse_reply(response.text)
            print('[登录响应] ' + reply_metadata(reply))
            if str(reply.get('result')) in ('1', 'ok'):
                print('登录接口报告成功。')
            else:
                print(login_failure_summary(reply))
                # An explicit rejection cannot be fixed by repeating slow external
                # HTTPS probes. Leave retries to the monitor's backoff timer.
                return False
    except (requests.RequestException, ValueError) as exc:
        print(f'登录请求未确认成功：{type(exc).__name__}')
    delays = (2, 4, 8) if verify_internet else (0, 1, 2)
    for attempt, delay in enumerate(delays, 1):
        print(f'[登录后验证] 第 {attempt}/3 次；等待 {delay} 秒')
        if delay:
            time.sleep(delay)
        online, _ = status(session, login_url)
        if not verify_internet:
            if online is True:
                print('登录后已确认认证在线；未验证外网可用性。')
                return True
            continue
        internet = connected(session)
        if online is True and internet:
            print('已确认认证在线，且至少一个外网检测地址可访问。')
            return True
    print('登录后未同时通过认证在线和外网检查。' if verify_internet else
          '登录后仍未确认认证在线，请查看认证接口日志。')
    return False


def login_failure_summary(reply):
    """Only emit bounded numeric codes and fixed messages, never raw response text."""
    codes = []
    for key in ('result', 'ret_code', 'msga', 'error', 'code'):
        value = str(reply.get(key, ''))
        if re.fullmatch(r'-?\d{1,6}', value):
            codes.append(f'{key}={value}')
    message = ' '.join(str(reply.get(k, '')) for k in ('msg', 'message', 'msga')).lower()
    reason = '具体原因未识别，请对照学校网页登录提示。'
    for markers, hint in [
        (('password', '密码'), '服务器提示密码相关错误，请核对校园网密码。'),
        (('不存在', 'not exist'), '服务器提示账号不存在，请核对账号及运营商。'),
        (('欠费', '余额', 'balance'), '服务器提示余额或欠费问题。'),
        (('绑定', 'bind'), '服务器提示设备绑定问题。'),
        (('在线', 'already online'), '服务器提示已有在线会话。'),
    ]:
        if any(marker in message for marker in markers):
            reason = hint
            break
    return '登录接口拒绝或未确认成功（' + (', '.join(codes) or '无可显示错误码') + '）。' + reason


def reconnect(session, login_url):
    """按学校网页注销并解绑本机 MAC；确认离线后再登录。"""
    print('开始注销重连。')
    online, data = status(session, login_url)
    if online is None:
        print('无法获取当前会话，取消注销，避免使用过期 IP/MAC。')
        return False
    offline_verified = online is False
    attempted_logout = False
    if online:
        configured = parse_qs(urlsplit(login_url).query).get('DDDDD', [''])[0].split('@')[0]
        account = str(data.get('uid', '')).split('@')[0]
        # olmac 是已认证终端的 MAC；ss4 可能是接入设备 MAC，不能混用。
        mac = re.sub(r'[:-]', '', str(data.get('olmac', ''))).upper()
        ip = str(data.get('v4ip') or data.get('v46ip') or '')
        try:
            address = ipaddress.IPv4Address(ip)
            if address.is_unspecified or not configured or account != configured:
                raise ValueError('会话不匹配')
            if not re.fullmatch(r'[0-9A-F]{12}', mac) or mac in ('000000000000', '111111111111', 'FFFFFFFFFFFF'):
                raise ValueError('无效 MAC')
        except ValueError:
            print('当前会话账号或终端 IP/MAC 无法验证，取消注销。')
            return False
        parts = urlsplit(login_url)
        endpoint = f'{parts.scheme}://{parts.hostname}:801/eportal/'
        params = {'c': 'Portal', 'a': 'unbind_mac', 'callback': 'dr1002',
                  'user_account': account, 'wlan_user_mac': mac,
                  'wlan_user_ip': ip, 'jsVersion': '3.3.2', 'v': time.time_ns()}
        print('使用当前在线会话参数，发送注销并解绑 MAC 请求。')
        attempted_logout = True
        try:
            with session.get(endpoint, params=params,
                             headers={'Referer': f'{parts.scheme}://{parts.netloc}/'},
                             timeout=(5, 10), allow_redirects=False) as response:
                response.raise_for_status()
                reply = parse_reply(response.text)
                print('解绑接口报告成功，等待离线确认。' if str(reply.get('result')) in ('1', 'ok')
                      else '解绑接口未确认成功，继续查询实际在线状态。')
        except (requests.RequestException, ValueError) as exc:
            print(f'解绑请求结果未知：{type(exc).__name__}；仍检查状态并尝试恢复登录。')
        for _ in range(6):
            time.sleep(2)
            state, _ = status(session, login_url)
            if state is False:
                offline_verified = True
                break
    if offline_verified:
        print('已确认离线；保持 10 秒，便于观察，然后自动登录。')
        time.sleep(10)
    elif attempted_logout:
        print('未观察到离线状态，本次退出不能算成功；仍尝试恢复登录。')
    restored = False
    for attempt in range(3):
        print(f'恢复登录，第 {attempt + 1}/3 次。')
        if cycle(session, login_url, True, force_login=True):
            restored = True
            break
        if attempt < 2:
            time.sleep(15)
    success = offline_verified and restored
    print('测试通过：已确认离线，再确认在线和外网可用。' if success else
          '测试未通过：未完成离线→在线→外网可用的完整验证。')
    return success


def next_daily_run(now):
    target = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def monitor(session, login_url, interval, daily):
    target = next_daily_run(datetime.now())
    failures = 0
    next_recovery = 0.0
    attempts = 0
    while True:
        try:
            now = datetime.now()
            if daily and now >= target:
                # 先推进计划，避免失败后反复注销；休眠唤醒补执行一次。
                target = next_daily_run(now)
                reconnect(session, login_url)
                next_recovery = time.monotonic() + 60
                failures = 0
            online, _ = status(session, login_url)
            internet = connected(session)
            if internet:
                failures = attempts = 0
                next_recovery = 0.0
                print('外网检测通过。' if online is True else
                      '外网可用，认证状态未确认；保留当前连接。')
            else:
                failures += 1
                print(f'连续外网检查失败：{failures} 次。')
                # 已在线时连续失败两次才注销；离线时可直接登录。
                ready = online is False or (online is True and failures >= 2)
                if ready and time.monotonic() >= next_recovery:
                    ok = (reconnect(session, login_url) if online else
                          cycle(session, login_url, True, force_login=True))
                    if ok:
                        failures = attempts = 0
                        next_recovery = 0.0
                    else:
                        attempts += 1
                        cooldown = min(1800, 60 * (2 ** min(attempts - 1, 5)))
                        next_recovery = time.monotonic() + cooldown
                        print(f'本轮恢复失败，至少 {cooldown} 秒后才再次认证；继续检查网络。')
                elif online is None:
                    print('认证服务器不可确认，等待网络恢复，不盲目解绑。')
            print(f'下次网络检查约 {interval} 秒后；每日重连：' +
                  (f'{target:%Y-%m-%d %H:%M:%S}' if daily else '关闭'))
        except Exception as exc:
            # 常驻模式容忍单轮故障，不输出可能含密码的 traceback。
            print(f'本轮异常：{type(exc).__name__}；下一轮继续。')
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description='校园网监测、登录与注销重连；默认每分钟检查。')
    parser.add_argument('--config', default=str(Path(__file__).resolve().with_name('config.json')))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-only', action='store_true', help='只查询，不改变连接')
    mode.add_argument('--login-once', action='store_true', help='尝试登录并验证一次')
    mode.add_argument('--reconnect-once', action='store_true', help='注销并重连，确认完整流程')
    parser.add_argument('--interval', type=int, default=60)
    parser.add_argument('--no-daily-reconnect', action='store_true', help='取消每日 04:00 注销重连')
    args = parser.parse_args()
    if args.interval < 30:
        parser.error('检查间隔至少 30 秒')
    root = Path(__file__).resolve().parent
    try:
        # 查询也使用同一个锁，防止另一实例重连期间读取中间状态。
        with OperationLock(root / 'AutoConnect.lock'):
            log_dir = root / 'logs'
            log_dir.mkdir(exist_ok=True)
            handler = TimedRotatingFileHandler(str(log_dir / 'AutoConnect.log'),
                                               when='midnight', backupCount=14, encoding='utf-8')
            handlers = [handler]
            import sys
            if sys.stdout is not None:
                handlers.append(logging.StreamHandler(sys.stdout))
            logging.basicConfig(level=logging.INFO, handlers=handlers, force=True,
                                format='%(asctime)s [%(process)d] %(message)s')
            print(f'启动版本 {VERSION}；PID={os.getpid()}；脚本={Path(__file__).resolve()}')
            try:
                url = load_login_url(args.config)
                parsed = urlsplit(url)
                query = parse_qs(parsed.query)
                if parsed.scheme not in ('http', 'https') or not query.get('DDDDD') or not query.get('upass'):
                    raise ValueError('配置不完整')
            except (OSError, SyntaxError, ValueError):
                print('配置读取失败：请检查 login_url 和 --config 文件。')
                return 2
            with requests.Session() as session:
                session.trust_env = False
                if args.reconnect_once:
                    return 0 if reconnect(session, url) else 1
                if args.check_only or args.login_once:
                    return 0 if cycle(session, url, args.login_once) else 1
                monitor(session, url, args.interval, not args.no_daily_reconnect)
    except RuntimeError:
        builtins.print('已有 AutoConnect 实例运行；请先结束计划任务再进行手动测试。')
        return 3
    except KeyboardInterrupt:
        print('已停止。')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
