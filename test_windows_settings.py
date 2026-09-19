import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import windows_settings as settings


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

    def test_auto_connect_requires_password_storage(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'preferences.json'
            with self.assertRaises(ValueError):
                settings.save_preferences(path, {'remember': False, 'auto_connect': True}, 'pw')
            self.assertFalse(path.exists())

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
