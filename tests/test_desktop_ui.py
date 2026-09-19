import logging
from pathlib import Path
import queue
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from campusconnect import desktop


class PanelLogTests(unittest.TestCase):
    def test_close_preference_saved_and_restored(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop, 'DATA', Path(folder)), \
             patch.object(desktop, 'startup_enabled', return_value=False), \
             patch.object(desktop, 'set_startup'), \
             patch.object(desktop, 'Tray'):
            root = tk.Tk()
            app = desktop.App(root)
            app.close_action.set('彻底退出')
            self.assertTrue(app.save())
            with patch.object(app, 'close') as quit_app, patch.object(app, 'hide') as hide:
                app.on_window_close()
                quit_app.assert_called_once()
                hide.assert_not_called()
            app.close()
            logging.shutdown()
            root = tk.Tk()
            app = desktop.App(root)
            self.assertEqual(app.saved_close_action, '彻底退出')
            app.close_action.set('隐藏到托盘')
            self.assertTrue(app.save())
            with patch.object(app, 'hide') as hide:
                app.on_window_close()
                hide.assert_called_once()
            app.close()
            logging.shutdown()

    def test_settings_page_switches_and_disabled_controls(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop, 'DATA', Path(folder)), \
             patch.object(desktop, 'startup_enabled', return_value=False), \
             patch.object(desktop, 'Tray'):
            root = tk.Tk()
            app = desktop.App(root)
            app.show_page('设置')
            root.update()
            switch = app.option_boxes[0]
            original = app.auto.get()
            switch.toggle()
            self.assertNotEqual(app.auto.get(), original)
            app.set_running(True)
            self.assertEqual(switch.cget('state'), 'disabled')
            self.assertTrue(all(button.cget('state') == 'disabled' for button in app.close_select._buttons_dict.values()))
            app.set_running(False)
            self.assertTrue(all(button.cget('state') == 'normal' for button in app.close_select._buttons_dict.values()))
            self.assertLessEqual(app.save_button.winfo_rooty() + app.save_button.winfo_height(),
                                 root.winfo_rooty() + root.winfo_height())
            app.close()
            logging.shutdown()

    def test_only_key_messages_and_no_duplicate_online(self):
        events = queue.Queue()
        handler = desktop.QueueLog(events)
        for message in ['[请求开始] 校园网登录', '[状态响应] 已识别字段=result',
                        '[子进程 123 2026-09-19] 已确认认证在线；未验证外网可用性。',
                        '下轮检查等待 60 秒；等待期间可点击停止',
                        '[子进程 123 2026-09-19] 已确认认证在线；未验证外网可用性。',
                        '登录接口拒绝或未确认成功（result=0）。', '下轮检查等待 120 秒']:
            handler.emit(logging.LogRecord('test', logging.INFO, '', 0, message, (), None))
        self.assertEqual(events.qsize(), 3)
        self.assertIn('已确认认证在线', events.get()[1])

    def test_hide_preserves_worker_restore_and_explicit_exit(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop, 'DATA', Path(folder)), \
             patch.object(desktop, 'startup_enabled', return_value=False), \
             patch.object(desktop, 'Tray') as tray:
            root = tk.Tk()
            app = desktop.App(root)
            root.update()
            task = MagicMock()
            task.process = None
            app.worker = task
            tray.return_value.ready.is_set.return_value = True
            app.hide()
            self.assertEqual(root.state(), 'withdrawn')
            task.stop.assert_not_called()
            app.events.put(('show', ''))
            app.poll()
            self.assertEqual(root.state(), 'normal')
            root.update_idletasks()
            self.assertLessEqual(app.log.winfo_rooty() + app.log.winfo_height(),
                                 root.winfo_rooty() + root.winfo_height())
            app.close()
            task.stop.assert_called_once()
            tray.return_value.stop.assert_called_once()
            logging.shutdown()


if __name__ == '__main__':
    unittest.main()
