"""Network diagnostics without emitting request queries, headers or response bodies."""
from contextlib import contextmanager
import logging
import time

import requests


def error_category(exc):
    # Inspect locally but never print the exception: requests exceptions may
    # contain the complete authentication URL and password.
    detail = str(exc).lower()
    if isinstance(exc, requests.exceptions.SSLError):
        for marker, category in [
            ('certificate_verify_failed', 'TLS 证书校验失败'),
            ('unexpected_eof', 'TLS 对端提前关闭连接'),
            ('eof occurred', 'TLS 对端提前关闭连接'),
            ('wrong_version_number', 'TLS 协议不匹配'),
            ('handshake', 'TLS 握手失败'),
        ]:
            if marker in detail:
                return category
        return 'TLS 连接失败（未分类）'
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return '建立连接超时'
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return '读取响应超时'
    if isinstance(exc, requests.exceptions.Timeout):
        return '请求超时'
    if isinstance(exc, requests.exceptions.ConnectionError):
        if any(marker in detail for marker in ('getaddrinfo', 'name resolution', 'nameresolution')):
            return 'DNS 解析失败'
        if 'refused' in detail or '10061' in detail:
            return '连接被拒绝'
        if 'reset' in detail or '10054' in detail:
            return '连接被重置'
        return '连接失败（未分类）'
    if isinstance(exc, requests.exceptions.HTTPError):
        return 'HTTP 状态码异常'
    return type(exc).__name__


@contextmanager
def measured_get(session, label, url, **kwargs):
    """label must be a caller-defined safe stage name, never a credential URL."""
    started = time.monotonic()
    logging.info('[请求开始] %s；GET；连接/读取超时=%s 秒；禁止重定向',
                 label, kwargs.get('timeout'))
    try:
        with session.get(url, **kwargs) as response:
            logging.info('[收到响应] %s；HTTP=%s；耗时=%.2f 秒',
                         label, response.status_code, time.monotonic() - started)
            yield response
    except requests.RequestException as exc:
        logging.info('[请求失败] %s；类型=%s；原因=%s；耗时=%.2f 秒',
                     label, type(exc).__name__, error_category(exc), time.monotonic() - started)
        raise
    except ValueError:
        logging.info('[解析失败] %s；响应不是预期的 JSON/JSONP 对象或字段无效；不记录原始正文', label)
        raise
    finally:
        logging.info('[请求结束] %s；总耗时=%.2f 秒', label, time.monotonic() - started)


def reply_metadata(reply):
    keys = ('result', 'ret_code', 'msga', 'msg', 'message', 'error', 'code')
    present = [key for key in keys if key in reply]
    return '已识别字段=' + (','.join(present) or '无')
