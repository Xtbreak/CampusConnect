import json
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

if sys.platform == 'darwin':
    from campusconnect import mac_settings as settings
    from keyring.errors import KeyringError


@unittest.skipUnless(sys.platform == 'darwin', 'macOS settings tests')
class MacSettingsTests(unittest.TestCase):
    def test_keychain_reference_and_forgetting(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'Keyring') as backend:
            path = Path(folder) / 'preferences.json'
            keychain = backend.return_value
            keychain.get_password.return_value = 'test secret 中文 '
            settings.save_preferences(path, {'remember': True}, 'test secret 中文 ')
            self.assertNotIn('test secret', path.read_text())
            self.assertEqual(settings.load_password(json.loads(path.read_text())), 'test secret 中文 ')
            keychain.set_password.assert_called_once_with(settings.SERVICE, settings.KEYCHAIN_ACCOUNT, 'test secret 中文 ')
            settings.save_preferences(path, {'remember': False}, '')
            keychain.delete_password.assert_called_once_with(settings.SERVICE, settings.KEYCHAIN_ACCOUNT)
            self.assertNotIn('password_keychain', path.read_text())

    def test_keychain_error_preserves_preferences(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'Keyring') as backend:
            path = Path(folder) / 'preferences.json'
            path.write_text('{"remember": false}')
            backend.return_value.set_password.side_effect = KeyringError('private diagnostic')
            with self.assertRaises(OSError):
                settings.save_preferences(path, {'remember': True}, 'secret')
            self.assertEqual(json.loads(path.read_text()), {'remember': False})
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_preferences_save_without_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'Keyring') as backend:
            backend.return_value.get_password.return_value = None
            path = Path(folder) / 'prefs.json'
            for remember in (False, True):
                settings.save_preferences(path, {'auto_connect': True, 'remember': remember}, '')
                saved = json.loads(path.read_text())
                self.assertTrue(saved['auto_connect'])
                self.assertEqual(saved['remember'], remember)
                self.assertNotIn('password_keychain', saved)
            backend.return_value.set_password.assert_not_called()

    def test_launch_agent_uses_argument_list_and_can_be_removed(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(settings, 'agent_path', return_value=Path(folder) / 'agent.plist'), \
             patch.object(settings.sys, 'frozen', True, create=True), \
             patch.object(settings.sys, 'executable', '/Applications/Campus App.app/Contents/MacOS/CampusConnect'):
            settings.set_startup(True)
            self.assertTrue(settings.startup_enabled())
            payload = plistlib.loads(settings.agent_path().read_bytes())
            self.assertEqual(payload['ProgramArguments'], ['/Applications/Campus App.app/Contents/MacOS/CampusConnect', '--startup'])
            self.assertNotIn('KeepAlive', payload)
            settings.set_startup(False)
            self.assertFalse(settings.startup_enabled())

    def test_source_startup_rejected(self):
        with patch.object(settings.sys, 'frozen', False, create=True):
            with self.assertRaises(ValueError):
                settings.startup_command()

    def test_translocated_app_startup_rejected(self):
        with patch.object(settings.sys, 'frozen', True, create=True), \
             patch.object(settings.sys, 'executable', '/private/var/folders/test/AppTranslocation/ID/d/CampusConnect.app/Contents/MacOS/CampusConnect'):
            with self.assertRaises(ValueError):
                settings.startup_command()

    def test_missing_keychain_password_is_not_silently_accepted(self):
        with patch.object(settings, 'Keyring') as backend:
            backend.return_value.get_password.return_value = None
            with self.assertRaises(ValueError):
                settings.load_password({'password_keychain': True})
