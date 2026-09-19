"""Tray callbacks communicate through a queue; only Tk's thread touches widgets."""
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw


def icon_image():
    source = Path(__file__).resolve().parent / 'assets' / 'campus-icon.png'
    if source.exists():
        with Image.open(source) as image:
            return image.convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, 62, 62), radius=16, fill='#2563eb')
    draw.arc((12, 14, 52, 54), 215, 325, fill='white', width=5)
    draw.arc((21, 25, 43, 47), 215, 325, fill='white', width=5)
    draw.ellipse((28, 40, 36, 48), fill='white')
    return image


class Tray:
    def __init__(self, events):
        self.events = events
        self.ready = threading.Event()
        self.icon = pystray.Icon('MyWatchCampus', icon_image(), '校园网助手', menu=pystray.Menu(
            pystray.MenuItem('显示窗口', lambda *_: events.put(('show', '')), default=True),
            pystray.MenuItem('设置', lambda *_: events.put(('settings', ''))),
            pystray.MenuItem('停止自动连接', lambda *_: events.put(('stop', ''))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出程序', lambda *_: events.put(('exit', ''))),
        ))
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        def setup(icon):
            icon.visible = True
            self.ready.set()
        try:
            self.icon.run(setup=setup)
        except Exception:
            self.events.put(('tray_error', ''))
        finally:
            self.ready.clear()

    def stop(self):
        self.icon.stop()
