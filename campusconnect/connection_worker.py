"""Isolated network worker so Stop can interrupt blocking DNS/TLS/socket calls."""
import logging
import multiprocessing
import time
from pathlib import Path

import requests
from campusconnect import core
from campusconnect.portal import build_login_url
from campusconnect.network import snapshot, connect_campus_wifi


class WorkerLog(logging.Handler):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def emit(self, record):
        self.events.put(('log', self.format(record)))


def auto_enabled(auto):
    return auto.is_set() if hasattr(auto, 'is_set') else bool(auto)


def wait_for_next_check(stop, auto, delay, network=None):
    deadline = time.monotonic() + delay
    next_network_check = time.monotonic() + 5
    while auto_enabled(auto):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        if stop.wait(min(0.2, remaining)):
            return False
        if network is not None and time.monotonic() >= next_network_check:
            if snapshot() != network:
                logging.info('网络接口或地址发生变化，提前重新检查。')
                return True
            next_network_check = time.monotonic() + 5
    return False


def mode_allows(network, mode):
    return network.allowed and (mode == 'auto' or network.kind == mode)


def run_connections(credentials, auto, data_dir, events, stop, wifi_auto=False, mode='auto'):
    logging.basicConfig(level=logging.INFO, handlers=[WorkerLog(events)], force=True,
                        format='[子进程 %(process)d %(asctime)s] %(message)s')
    logging.info('网络任务启动；运营商=%s；持续监测=%s；环境代理=关闭；先处理校园网认证，再检测外网',
                 credentials[2] if credentials[2] in ('电信', '移动', '联通') else '未知', auto_enabled(auto))
    try:
        with core.OperationLock(Path(data_dir) / 'AutoConnect.lock'), requests.Session() as session:
            logging.info('已取得连接操作锁')
            session.trust_env = False
            failures = 0
            round_number = 0
            previous_network = None
            previous_message = None
            next_wifi_attempt = 0
            while not stop.is_set():
                network = snapshot()
                if (auto_enabled(wifi_auto) and not network.allowed
                        and network.kind in ('offline', 'wifi')
                        and time.monotonic() >= next_wifi_attempt and not stop.is_set()):
                    message = '正在尝试连接 AUST_Student Wi-Fi……'
                    logging.info(message)
                    events.put(('state', message))
                    requested = connect_campus_wifi(network)
                    if requested:
                        # netsh success only means accepted. Wait for the actual
                        # route/SSID before sending any campus credentials.
                        for _ in range(15):
                            if stop.wait(1) or not auto_enabled(wifi_auto):
                                break
                            network = snapshot()
                            if network.allowed:
                                break
                    next_wifi_attempt = time.monotonic() + 60
                    if stop.is_set():
                        break
                    if not network.allowed:
                        message = '未连接到 AUST_Student：请先在 Windows 手动连接一次并保存配置，检查 Wi-Fi 开关及信号。'
                        logging.info(message)
                        events.put(('state', message))
                        previous_message = network.message
                if network != previous_network:
                    session.close()
                    session.cookies.clear()
                    failures = 0
                    previous_network = network
                    logging.info('网络环境更新；类型=%s；校园 Wi-Fi=%s',
                                 network.kind, network.kind == 'wifi' and network.allowed)
                if not mode_allows(network, mode):
                    message = network.message if not network.allowed else (
                        '已选择无线连接，但门户当前走有线网络；请拔掉网线或切换为有线连接。'
                        if mode == 'wifi' else '已选择有线连接，请插入校园网线或切换为无线连接。')
                    if previous_message != message:
                        logging.info(message)
                        events.put(('state', message))
                        previous_message = message
                    if not auto_enabled(auto) or not wait_for_next_check(stop, auto, 5):
                        break
                    continue
                previous_message = None
                round_number += 1
                started = time.monotonic()
                logging.info('[轮次 %d] 开始；此前连续失败=%d', round_number, failures)
                authenticated = core.cycle(session, build_login_url(*credentials), True, verify_internet=False,
                                           login_guard=lambda: not stop.is_set() and snapshot() == network)
                # Probe after authentication so an offline external site does not
                # delay login or trigger repeated login of an existing session.
                ok = core.connected(session)
                failures = 0 if ok else failures + 1
                logging.info('[轮次 %d] 结束；成功=%s；连续失败=%d；耗时=%.2f 秒',
                             round_number, ok, failures, time.monotonic() - started)
                if ok:
                    message = '网络已连接；自动检查中。' if auto_enabled(auto) else '网络已连接。'
                    logging.info('网络已连接。')
                else:
                    message = ('外网检测失败：校园网已认证，但暂时无法确认外网可用。' if authenticated else
                               '外网检测失败：校园网认证也未确认，请检查网络连接或账号信息。')
                    logging.info(message)
                events.put(('state', message))
                if not auto_enabled(auto):
                    logging.info('单次连接任务完成')
                    break
                delay = min(1800, 60 * 2 ** min(failures, 5))
                logging.info('下轮检查等待 %d 秒；等待期间可点击停止', delay)
                if not wait_for_next_check(stop, auto, delay, network):
                    if not stop.is_set() and ok:
                        events.put(('state', '网络已连接。'))
                    break
    except RuntimeError:
        logging.info('连接操作锁被占用，退出本次任务')
        events.put(('state', '已有连接任务运行，请先停止另一个实例。'))
    except Exception as exc:
        logging.info('网络任务异常退出；异常类型=%s（不记录可能含凭据的异常正文）', type(exc).__name__)
        events.put(('state', '连接任务失败：' + type(exc).__name__))
    finally:
        logging.info('网络任务结束')


class ConnectionTask:
    def __init__(self):
        self.context = multiprocessing.get_context('spawn')
        self.process = None
        self.events = None
        self.stop_event = None
        self.auto_event = None
        self.wifi_event = None
        self.stopping = False

    def is_alive(self):
        return self.process is not None and self.process.is_alive()

    def start(self, credentials, auto, data_dir, wifi_auto=False, mode='auto'):
        if self.is_alive():
            raise RuntimeError('连接任务尚未结束')
        self.dispose()
        self.stopping = False
        self.events = self.context.Queue()
        self.stop_event = self.context.Event()
        self.auto_event = self.context.Event()
        self.wifi_event = self.context.Event()
        self.set_auto(auto)
        self.set_wifi_auto(wifi_auto)
        self.process = self.context.Process(target=run_connections,
            args=(credentials, self.auto_event, str(data_dir), self.events, self.stop_event, self.wifi_event, mode), daemon=True)
        self.process.start()

    def set_wifi_auto(self, enabled):
        if self.wifi_event is not None:
            if enabled:
                self.wifi_event.set()
            else:
                self.wifi_event.clear()

    def set_auto(self, enabled):
        if self.auto_event is not None:
            if enabled:
                self.auto_event.set()
            else:
                self.auto_event.clear()

    def stop(self):
        self.stopping = True
        if self.stop_event:
            self.stop_event.set()
        if self.is_alive():
            self.process.terminate()
        # A forcibly stopped process can leave its queue half-written. Never read
        # that queue again; the next run always gets a fresh queue and event.

    def dispose(self):
        if self.is_alive():
            return
        if self.process is not None:
            self.process.join()
            self.process.close()
            self.process = None
        if self.events is not None:
            self.events.close()
            self.events = None
