"""Isolated network worker so Stop can interrupt blocking DNS/TLS/socket calls."""
import logging
import multiprocessing
import time
from pathlib import Path

import requests
from campusconnect import core
from campusconnect.portal import build_login_url


class WorkerLog(logging.Handler):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def emit(self, record):
        self.events.put(('log', self.format(record)))


def run_connections(credentials, auto, data_dir, events, stop):
    logging.basicConfig(level=logging.INFO, handlers=[WorkerLog(events)], force=True,
                        format='[子进程 %(process)d %(asctime)s] %(message)s')
    logging.info('网络任务启动；运营商=%s；持续监测=%s；环境代理=关闭；仅查询校园网认证状态，不检测外网',
                 credentials[2] if credentials[2] in ('电信', '移动', '联通') else '未知', auto)
    try:
        with core.OperationLock(Path(data_dir) / 'AutoConnect.lock'), requests.Session() as session:
            logging.info('已取得连接操作锁')
            session.trust_env = False
            failures = 0
            round_number = 0
            while not stop.is_set():
                round_number += 1
                started = time.monotonic()
                logging.info('[轮次 %d] 开始；此前连续失败=%d', round_number, failures)
                ok = core.cycle(session, build_login_url(*credentials), True, verify_internet=False)
                failures = 0 if ok else failures + 1
                logging.info('[轮次 %d] 结束；成功=%s；连续失败=%d；耗时=%.2f 秒',
                             round_number, ok, failures, time.monotonic() - started)
                events.put(('state', '认证在线；自动检查中（未检测外网）。' if ok and auto else
                            '认证在线（未检测外网）。' if ok else '认证未确认，请查看上方认证错误提示。'))
                if not auto:
                    logging.info('单次连接任务完成')
                    break
                delay = min(1800, 60 * 2 ** min(failures, 5))
                logging.info('下轮检查等待 %d 秒；等待期间可点击停止', delay)
                if stop.wait(delay):
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
        self.stopping = False

    def is_alive(self):
        return self.process is not None and self.process.is_alive()

    def start(self, credentials, auto, data_dir):
        if self.is_alive():
            raise RuntimeError('连接任务尚未结束')
        self.dispose()
        self.stopping = False
        self.events = self.context.Queue()
        self.stop_event = self.context.Event()
        self.process = self.context.Process(target=run_connections,
            args=(credentials, auto, str(data_dir), self.events, self.stop_event), daemon=True)
        self.process.start()

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
