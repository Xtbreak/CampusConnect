import sys
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

if sys.platform == 'win32':
    from campusconnect import windows_settings as settings


@unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI and registry tests')
class SettingsTests(unittest.TestCase):
    def test_encrypted_persistence_and_forgetting(self):
        password = 'example +&中文 password '
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'preferences.json'
            settings.save_preferences(path, {'remember': True, 'auto_connect': True}, password)
            content = path.read_text(encoding='utf-8')
            self.assertNotIn(password, content)
            self.assertEqual(settings.unprotect(json.loads(content)['password_dpapi']), password)
            settings.save_preferences(path, {'remember': False, 'auto_connect': False}, password)
            self.assertNotIn('password_dpapi', path.read_text())

    def test_preferences_save_without_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'preferences.json'
            for remember in (False, True):
                settings.save_preferences(path, {'remember': remember, 'auto_connect': True}, '')
                saved = json.loads(path.read_text())
                self.assertTrue(saved['auto_connect'])
                self.assertEqual(saved['remember'], remember)
                self.assertNotIn('password_dpapi', saved)

    def test_startup_command_and_registry_scope(self):
        with patch.object(settings.sys, 'frozen', True, create=True), \
             patch.object(settings.sys, 'executable', r'C:\Campus App\CampusConnect.exe'), \
             patch.object(settings.winreg, 'CreateKey') as create, \
             patch.object(settings.winreg, 'SetValueEx') as write, \
             patch.object(settings.winreg, 'DeleteValue') as delete:
            settings.set_startup(True)
            create.assert_called_with(settings.winreg.HKEY_CURRENT_USER, settings.RUN_KEY)
            self.assertEqual(write.call_args.args[-1], '"C:\\Campus App\\CampusConnect.exe" --startup')
            settings.set_startup(False)
            self.assertEqual(delete.call_args.args[-1], settings.RUN_NAME)


if __name__ == '__main__':
    unittest.main()
