"""Windows network detection and opt-in connection to a saved campus profile."""
from dataclasses import dataclass
import json
import os
import re
import socket
import subprocess

CAMPUS_SSID = 'AUST_Student'


def connect_campus_wifi(current):
    """Submit a connection request, not proof of association or authentication.

    Never create an open-network profile or change Windows auto-connect settings.
    The saved profile must have the same name as the campus SSID.
    """
    if os.name != 'nt' or current.allowed or current.kind not in ('offline', 'wifi'):
        return False
    args = ['netsh.exe', 'wlan', 'connect', f'name={CAMPUS_SSID}', f'ssid={CAMPUS_SSID}']
    if current.kind == 'wifi' and current.interface:
        args.append(f'interface={current.interface}')
    try:
        command(args)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


@dataclass(frozen=True)
class Network:
    address: str = ''
    interface: str = ''
    kind: str = 'unknown'
    ssid: str = ''

    @property
    def allowed(self):
        return self.kind in ('wired', 'legacy') or (
            self.kind == 'wifi' and self.ssid == CAMPUS_SSID)

    @property
    def message(self):
        if self.kind == 'offline':
            return '等待网络连接，请连接 AUST_Student 或校园网线。'
        if self.kind == 'wifi':
            return '当前 Wi-Fi 不是 AUST_Student 或无法读取名称，已暂停校园网认证。'
        return '无法确认校园网使用的网络接口，已暂停认证。'


def command(args):
    return subprocess.run(args, capture_output=True, timeout=4, check=True,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout


def wifi_ssid(text, interface):
    # Match the adapter name as a value, independent of the localized "Name" key.
    # Only the exact SSID key is accepted (never BSSID).
    selected = False
    for line in text.splitlines():
        if not line.strip():
            selected = False
        if ':' not in line:
            continue
        key, value = (part.strip() for part in line.split(':', 1))
        if value == interface:
            selected = True
        if selected and re.fullmatch(r'SSID', key, re.I):
            return value
    return ''


def snapshot():
    if os.name != 'nt':
        # macOS keeps its existing portal checks; Windows WLAN handling is not
        # silently presented as a tested macOS SSID implementation.
        return Network(kind='legacy')
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect(('10.255.0.19', 80))  # Route lookup only; no packet sent.
            address = route.getsockname()[0]
    except OSError:
        return Network(kind='offline')
    try:
        # address comes from the OS, not from user input or a portal response.
        socket.inet_aton(address)
        script = (
            '[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();'
            "$ErrorActionPreference='Stop';"
            f"$campusIp=Get-NetIPAddress -AddressFamily IPv4 -IPAddress '{address}';"
            '$campusAdapter=Get-NetAdapter -IncludeHidden | Where-Object '
            '{$_.ifIndex -eq $campusIp.InterfaceIndex};'
            '$campusAdapter | Select-Object Name,InterfaceType | ConvertTo-Json -Compress'
        )
        data = json.loads(command(['powershell.exe', '-NoProfile', '-NonInteractive',
                                   '-Command', script]).decode('utf-8-sig'))
        interface = data['Name']
        kind = {6: 'wired', 71: 'wifi'}.get(int(data['InterfaceType']), 'unknown')
        ssid = ''
        if kind == 'wifi':
            import ctypes
            encoding = 'cp' + str(ctypes.windll.kernel32.GetOEMCP())
            output = command(['netsh.exe', 'wlan', 'show', 'interfaces']).decode(encoding, errors='replace')
            ssid = wifi_ssid(output, interface)
        return Network(address, interface, kind, ssid)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return Network(address=address)
