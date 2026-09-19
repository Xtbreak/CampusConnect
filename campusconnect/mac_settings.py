"""macOS login Keychain and per-user, next-login LaunchAgent."""
import json
from pathlib import Path
import plistlib
import sys

from keyring.backends.macOS import Keyring
from keyring.errors import KeyringError

SERVICE = 'io.github.xtbreak.CampusConnect'
KEYCHAIN_ACCOUNT = 'campus-password'
AGENT_LABEL = 'io.github.xtbreak.CampusConnect'


def agent_path():
    return Path.home() / 'Library' / 'LaunchAgents' / (AGENT_LABEL + '.plist')


def startup_command():
    executable = Path(sys.executable).resolve()
    if not getattr(sys, 'frozen', False) or executable.parent.name != 'MacOS' or executable.parent.parent.name != 'Contents':
        raise ValueError('登录时启动需要使用打包后的 App，请先移至“应用程序”文件夹。')
    if 'AppTranslocation' in executable.parts:
        raise ValueError('请先将 App 移至“应用程序”文件夹，重新打开后再启用登录时启动。')
    return [str(executable), '--startup']


def set_startup(enabled):
    path = agent_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    payload = {'Label': AGENT_LABEL, 'ProgramArguments': startup_command(),
               'RunAtLoad': True, 'LimitLoadToSessionType': 'Aqua'}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(plistlib.dumps(payload))
    temporary.chmod(0o600)
    temporary.replace(path)


def startup_enabled():
    path = agent_path()
    if not path.exists():
        return False
    try:
        payload = plistlib.loads(path.read_bytes())
        return payload.get('Label') == AGENT_LABEL and payload.get('RunAtLoad') is True
    except (OSError, ValueError, plistlib.InvalidFileException, AttributeError):
        return False


def load_password(settings):
    if not settings.get('password_keychain'):
        return ''
    try:
        password = Keyring().get_password(SERVICE, KEYCHAIN_ACCOUNT)
    except KeyringError as exc:
        raise OSError('无法读取系统钥匙串。') from exc
    if password is None:
        raise ValueError('钥匙串中未找到密码，请重新填写并保存。')
    return password


def save_preferences(path, settings, password):
    payload = dict(settings)
    payload.pop('password_dpapi', None)
    payload.pop('password_keychain', None)
    # Write a safe settings file first; it contains only a reference to Keychain.
    if payload.get('remember') and password:
        payload['password_keychain'] = True
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    temporary.chmod(0o600)
    try:
        keychain = Keyring()
        if payload.get('remember') and password:
            keychain.set_password(SERVICE, KEYCHAIN_ACCOUNT, password)
        else:
            # Check before deletion so a missing entry is harmless, but an actual
            # Keychain failure is surfaced instead of reporting "forgotten".
            if keychain.get_password(SERVICE, KEYCHAIN_ACCOUNT) is not None:
                keychain.delete_password(SERVICE, KEYCHAIN_ACCOUNT)
        temporary.replace(path)
    except KeyringError as exc:
        raise OSError('无法更新系统钥匙串。') from exc
    finally:
        temporary.unlink(missing_ok=True)
