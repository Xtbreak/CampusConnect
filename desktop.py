"""无需命令行的 Windows 校园网客户端。"""
import json
import logging
import os
from pathlib import Path
import queue
import multiprocessing
import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox
from logging.handlers import TimedRotatingFileHandler

from connection_worker import ConnectionTask
from AutoConnect import VERSION
from portal import OPERATORS, build_login_url
from windows_settings import save_preferences, unprotect, set_startup, startup_enabled
from tray import Tray

DATA = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'MyWatch'


class QueueLog(logging.Handler):
    def __init__(self, events):
        super().__init__()
        self.events = events
        self.previous = None

    def emit(self, record):
        message = re.sub(r'^\[子进程 [^\]]+\]\s*', '', record.getMessage())
        prefixes = ('程序启动', '设置已保存', '设置保存失败', '连接参数验证失败',
                    '准备启动独立网络任务', '创建网络子进程失败',
                    '发送登录请求', '登录接口', '登录请求未确认',
                    '登录后已确认', '登录后仍未确认', '已确认认证在线',
                    '认证状态：未知', '连接操作锁被占用', '网络任务异常',
                    '下轮检查等待', '用户停止', '托盘不可用')
        if not message.startswith(prefixes):
            return
        if message.startswith('下轮检查等待 60 秒'):
            return
        if message == self.previous:
            return
        self.previous = message
        if message.startswith('程序启动'):
            message = '校园网助手已启动。'
        elif message.startswith('准备启动独立网络任务'):
            message = '正在连接校园网……'
        record = logging.makeLogRecord({**record.__dict__, 'msg': message, 'args': ()})
        self.events.put(('log', self.format(record)))


class App:
    def __init__(self, root):
        self.root = root
        root.title('校园网助手')
        root.geometry('660x720')
        root.minsize(620, 680)
        root.configure(background='#f3f6fb')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        style.configure('TFrame', background='#f3f6fb')
        style.configure('TLabel', background='#f3f6fb', foreground='#172b4d')
        style.configure('Card.TFrame', background='white')
        style.configure('Card.TLabel', background='white', foreground='#334155')
        style.configure('TCheckbutton', background='white', padding=5)
        style.map('TCheckbutton', background=[('active', '#eff6ff')])
        style.configure('TEntry', padding=8)
        style.configure('TCombobox', padding=8)
        style.configure('TButton', padding=(12, 8))
        style.configure('Primary.TButton', foreground='white', background='#2563eb')
        style.map('Primary.TButton', background=[('disabled', '#cbd5e1'), ('active', '#1d4ed8')])
        self.events = queue.Queue()
        self.worker = ConnectionTask()
        self.running = False
        self.exiting = False
        DATA.mkdir(parents=True, exist_ok=True)
        self.account = tk.StringVar()
        self.password = tk.StringVar()
        self.operator = tk.StringVar()
        self.auto = tk.BooleanVar(value=True)
        self.remember = tk.BooleanVar(value=False)
        self.autostart = tk.BooleanVar(value=startup_enabled())
        self.auto_connect = tk.BooleanVar(value=False)
        self.close_action = tk.StringVar(value='隐藏到托盘')
        self.saved_close_action = '隐藏到托盘'
        self.state = tk.StringVar(value='请填写校园网账号、密码并选择运营商。')
        try:
            settings = json.loads((DATA / 'preferences.json').read_text(encoding='utf-8'))
            self.account.set(settings.get('account', ''))
            if settings.get('operator') in OPERATORS:
                self.operator.set(settings['operator'])
            self.auto.set(bool(settings.get('auto', True)))
            self.remember.set(bool(settings.get('remember', False)))
            self.auto_connect.set(bool(settings.get('auto_connect', False)))
            self.saved_close_action = settings.get('close_action', '隐藏到托盘')
            if self.saved_close_action not in ('隐藏到托盘', '彻底退出'):
                self.saved_close_action = '隐藏到托盘'
            self.close_action.set(self.saved_close_action)
            if self.remember.get() and settings.get('password_dpapi'):
                self.password.set(unprotect(settings['password_dpapi']))
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError):
            self.auto_connect.set(False)
            self.state.set('未能读取设置或解密密码，请重新填写并保存。')
        from ui_layout import build
        build(self)
        icon = Path(__file__).resolve().parent / 'assets' / 'campus.ico'
        if icon.exists():
            root.iconbitmap(str(icon))
        log_handler = QueueLog(self.events)
        log_handler.setFormatter(logging.Formatter('%(asctime)s  %(message)s', datefmt='%H:%M:%S'))
        file_handler = TimedRotatingFileHandler(DATA / 'client.log', when='midnight',
                                                backupCount=14, encoding='utf-8')
        logging.basicConfig(level=logging.INFO, handlers=[log_handler, file_handler],
                            format='%(asctime)s [主进程 %(process)d] %(message)s', force=True)
        logging.info('程序启动；版本=%s；打包运行=%s；启动方式=%s', VERSION,
                     bool(getattr(sys, 'frozen', False)), '开机启动' if '--startup' in sys.argv else '手动打开')
        logging.info('设置状态：记住密码=%s；密码已载入=%s；自动连接=%s；持续监测=%s；开机启动=%s',
                     self.remember.get(), bool(self.password.get()), self.auto_connect.get(),
                     self.auto.get(), self.autostart.get())
        self.tray = None
        try:
            self.tray = Tray(self.events)
        except Exception:
            logging.info('托盘不可用，关闭按钮将最小化到任务栏。')
        root.protocol('WM_DELETE_WINDOW', self.on_window_close)
        root.after(100, self.poll)
        if self.auto_connect.get() and self.remember.get() and self.password.get():
            root.after(500, self.start)
            logging.info('已安排启动后自动连接，延迟 0.5 秒')
            if '--startup' in sys.argv:
                root.after(600, self.hide)

    def hide(self):
        if self.tray is not None and self.tray.ready.is_set():
            self.root.withdraw()
            logging.info('窗口已隐藏到系统托盘，网络任务保持运行')
        else:
            self.root.iconify()
            logging.info('托盘不可用，窗口已最小化到任务栏')

    def on_window_close(self):
        if self.saved_close_action == '彻底退出':
            self.close()
        else:
            self.hide()

    def show(self):
        self.root.deiconify()
        self.root.lift()


    def save(self):
        try:
            if self.auto_connect.get():
                build_login_url(self.account.get(), self.password.get(), self.operator.get())
            # Apply startup only when the user saves or clicks Connect.
            previous_startup = startup_enabled()
            set_startup(self.autostart.get())
            try:
                save_preferences(DATA / 'preferences.json', {
                    'account': self.account.get().strip(), 'operator': self.operator.get(),
                    'remember': self.remember.get(), 'auto_connect': self.auto_connect.get(),
                    'auto': self.auto.get(), 'close_action': self.close_action.get(),
                }, self.password.get())
            except (OSError, ValueError):
                if previous_startup != self.autostart.get():
                    set_startup(previous_startup)
                raise
        except (ValueError, OSError) as exc:
            logging.info('设置保存失败；异常类型=%s', type(exc).__name__)
            messagebox.showerror('无法保存', str(exc) if isinstance(exc, ValueError) else '设置保存失败，请检查本地文件和启动项权限。')
            return False
        self.saved_close_action = self.close_action.get()
        self.state.set('设置已保存。')
        logging.info('设置已保存；记住密码=%s；开机启动=%s；自动连接=%s；持续监测=%s',
                     self.remember.get(), self.autostart.get(), self.auto_connect.get(), self.auto.get())
        return True

    def open_logs(self):
        try:
            os.startfile(str(DATA))
        except OSError:
            messagebox.showerror('打开日志失败', f'请手动打开日志目录：{DATA}')

    def start(self):
        if self.running:
            logging.info('忽略重复连接：当前任务尚未结束')
            return
        try:
            build_login_url(self.account.get(), self.password.get(), self.operator.get())
        except (ValueError, OSError) as exc:
            logging.info('连接参数验证失败；未发送网络请求')
            messagebox.showerror('无法连接', str(exc) if isinstance(exc, ValueError) else '无法保存本地设置。')
            return
        if not self.save():
            return
        self.running = True
        self.set_running(True)
        self.state.set('正在检查并连接校园网……')
        credentials = (self.account.get(), self.password.get(), self.operator.get())
        try:
            logging.info('准备启动独立网络任务')
            self.worker.start(credentials, self.auto.get(), DATA)
            logging.info('网络子进程已创建；PID=%s', self.worker.process.pid)
        except (OSError, RuntimeError):
            logging.info('创建网络子进程失败')
            self.running = False
            self.set_running(False)
            self.state.set('无法启动连接任务，请关闭后重新打开程序。')

    def set_running(self, running):
        for widget in self.inputs:
            widget.configure(state='disabled' if running else 'normal')
        self.select.configure(state='disabled' if running else 'readonly')
        for checkbox in self.option_boxes:
            checkbox.configure(state='disabled' if running else 'normal')
        self.close_select.configure(state='disabled' if running else 'normal')
        self.save_button.configure(state='disabled' if running else 'normal')
        self.start_button.configure(state='disabled' if running else 'normal')
        self.stop_button.configure(state='normal' if running else 'disabled')

    def stop_work(self):
        logging.info('收到停止操作；网络任务运行中=%s；将终止网络子进程', self.worker.is_alive())
        self.worker.stop()
        self.stop_button.configure(state='disabled')
        self.state.set('正在终止网络任务……')

    def poll(self):
        if self.exiting:
            return
        if self.running and not self.worker.stopping and self.worker.events is not None:
            while True:
                try:
                    kind, value = self.worker.events.get_nowait()
                except queue.Empty:
                    break
                if kind == 'log':
                    logging.info(value)
                elif kind == 'state':
                    self.state.set(value)
        if self.running and not self.worker.is_alive():
            logging.info('网络子进程已退出；退出码=%s；用户主动停止=%s',
                         self.worker.process.exitcode if self.worker.process else '未创建', self.worker.stopping)
            self.running = False
            self.set_running(False)
            if self.worker.stopping:
                self.state.set('已停止，现有网络连接保留。已发出的认证请求无法撤回。')
                logging.info('用户停止：网络任务已终止，不再发送后续请求。')
            self.worker.dispose()
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'log':
                self.log.configure(state='normal')
                self.log.insert('end', value + '\n')
                if int(self.log.index('end-1c').split('.')[0]) > 250:
                    self.log.delete('1.0', '50.0')
                self.log.see('end')
                self.log.configure(state='disabled')
            elif kind == 'show':
                self.show()
            elif kind == 'settings':
                self.show()
                self.show_page('设置')
            elif kind == 'stop':
                if self.running:
                    self.stop_work()
            elif kind == 'exit':
                self.close()
                return
            elif kind == 'tray_error':
                logging.info('托盘不可用，已恢复主窗口。')
                self.show()
        self.root.after(100, self.poll)

    def close(self):
        self.exiting = True
        logging.info('关闭窗口；终止剩余网络任务')
        self.worker.stop()
        if self.worker.process is not None:
            self.worker.process.join(timeout=1)
        self.worker.dispose()
        if self.tray is not None:
            self.tray.stop()
        logging.info('程序关闭')
        for timer in self.root.tk.call('after', 'info'):
            self.root.after_cancel(timer)
        self.root.destroy()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    root = tk.Tk()
    App(root)
    root.mainloop()
