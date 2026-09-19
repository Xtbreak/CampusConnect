import logging
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from campusconnect import desktop


class DesktopTests(unittest.TestCase):
    def test_empty_credentials_allow_save_but_block_login(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop, 'DATA', Path(folder)), \
             patch.object(desktop, 'startup_enabled', return_value=False), \
             patch.object(desktop, 'set_startup'), \
             patch.object(desktop, 'Tray'), \
             patch.object(desktop.messagebox, 'showerror') as error:
            root = tk.Tk()
            app = desktop.App(root)
            root.update()
            try:
                self.assertTrue(all(option.get() for option in
                                    (app.auto, app.remember, app.autostart, app.auto_connect)))
                app.auto_connect.set(True)
                app.remember.set(True)
                with patch.object(desktop, 'build_login_url') as validate:
                    self.assertTrue(app.save())
                    validate.assert_not_called()
                error.assert_not_called()
                with patch.object(app.worker, 'start') as start:
                    for account, password in [('', ''), ('student', ''), ('', 'pw')]:
                        app.account.set(account)
                        app.password.set(password)
                        app.start()
                    start.assert_not_called()
                self.assertEqual(error.call_count, 3)
            finally:
                app.close()
                logging.shutdown()

    def setUp(self):
        # UI tests must never touch the user's real Keychain.
        if desktop.IS_MAC:
            from campusconnect import mac_settings
            backend = patch.object(mac_settings, 'Keyring')
            backend.start().return_value.get_password.return_value = None
            self.addCleanup(backend.stop)

    def test_close_preference_saved_and_restored(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop, 'DATA', Path(folder)), \
             patch.object(desktop, 'startup_enabled', return_value=False), \
             patch.object(desktop, 'set_startup'), \
             patch.object(desktop, 'Tray'):
            root = tk.Tk()
            app = desktop.App(root)
            root.update()
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
            root.update()
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
            root.update()
            app.show_page('设置')
            root.geometry('620x680')
            root.update()
            for value, button in app.close_select._buttons_dict.items():
                self.assertTrue(button.winfo_ismapped())
                self.assertGreater(button.winfo_width(), 90)
                self.assertGreater(button.winfo_height(), 25)
                self.assertLessEqual(button.winfo_rooty() + button.winfo_height(),
                                     root.winfo_rooty() + root.winfo_height())
                button.invoke()
                self.assertEqual(app.close_action.get(), value)
            switch = app.option_boxes[0]
            original = app.auto.get()
            switch.toggle()
            self.assertNotEqual(app.auto.get(), original)
            app.set_running(True)
            self.assertEqual(switch.cget('state'), 'normal')
            self.assertEqual(app.save_button.cget('state'), 'normal')
            self.assertTrue(all(w.cget('state') == 'disabled' for w in app.inputs))
            self.assertTrue(all(button.cget('state') == 'normal' for button in app.close_select._buttons_dict.values()))
            app.set_running(False)
            self.assertTrue(all(button.cget('state') == 'normal' for button in app.close_select._buttons_dict.values()))
            self.assertLessEqual(app.save_button.winfo_rooty() + app.save_button.winfo_height(),
                                 root.winfo_rooty() + root.winfo_height())
            app.close()
            logging.shutdown()

    def test_save_while_connected_updates_monitor_without_restarting(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop, 'DATA', Path(folder)), \
             patch.object(desktop, 'startup_enabled', return_value=False), \
             patch.object(desktop, 'set_startup'), \
             patch.object(desktop, 'Tray'):
            root = tk.Tk()
            app = desktop.App(root)
            root.update()
            try:
                task = MagicMock()
                task.process = None
                app.worker = task
                app.running = True
                app.set_running(True)
                app.state.set('网络已连接。')
                app.auto.set(False)
                app.close_action.set('彻底退出')
                self.assertTrue(app.save())
                task.set_auto.assert_called_once_with(False)
                task.stop.assert_not_called()
                task.start.assert_not_called()
                self.assertEqual(app.state.get(), '网络已连接。')
                self.assertEqual(app.saved_close_action, '彻底退出')
                with patch.object(desktop, 'save_preferences', side_effect=OSError), \
                     patch.object(desktop.messagebox, 'showerror'):
                    app.auto.set(True)
                    self.assertFalse(app.save())
                task.set_auto.assert_called_once_with(False)
            finally:
                app.close()
                logging.shutdown()

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
            self.assertLessEqual(app.start_button.winfo_rooty() + app.start_button.winfo_height(),
                                 root.winfo_rooty() + root.winfo_height())
            app.close()
            task.stop.assert_called_once()
            tray.return_value.stop.assert_called_once()
            logging.shutdown()


if __name__ == '__main__':
    unittest.main()
