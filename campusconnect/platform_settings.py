"""Platform boundary for desktop preferences and shell integration."""
import os
from pathlib import Path
import subprocess
import sys

IS_MAC = sys.platform == 'darwin'
FONT_FAMILY = 'PingFang SC' if IS_MAC else 'Microsoft YaHei UI'

if IS_MAC:
    from campusconnect.mac_settings import save_preferences, load_password, set_startup, startup_enabled
else:
    from campusconnect.windows_settings import save_preferences, set_startup, startup_enabled, unprotect

    def load_password(settings):
        return unprotect(settings['password_dpapi']) if settings.get('password_dpapi') else ''


def data_directory():
    if IS_MAC:
        return Path.home() / 'Library' / 'Application Support' / 'CampusConnect'
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'MyWatch'


def open_directory(path):
    if IS_MAC:
        result = subprocess.run(['/usr/bin/open', str(path)], check=False)
        if result.returncode:
            raise OSError('无法打开文件夹。')
    else:
        os.startfile(str(path))
