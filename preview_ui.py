"""Capture only our own temporary, credential-free UI for layout review."""
import logging
from pathlib import Path
import tempfile
from unittest.mock import patch
import tkinter as tk
from PIL import ImageGrab
import desktop


if __name__ == '__main__':
    output = Path(__file__).resolve().parent / 'dist' / 'ui-review'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder, patch.object(desktop, 'DATA', Path(folder)), \
         patch.object(desktop, 'startup_enabled', return_value=False), patch.object(desktop, 'Tray'):
        root = tk.Tk()
        app = desktop.App(root)
        root.geometry('900x700+100+80')
        root.attributes('-topmost', True)
        def capture(name):
            root.update_idletasks()
            x, y = root.winfo_rootx(), root.winfo_rooty()
            ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height())).save(output / name)
        def settings():
            capture('connection.png')
            app.show_page('设置')
            root.after(500, finish)
        def finish():
            capture('settings.png')
            app.close()
        root.after(700, settings)
        root.mainloop()
        logging.shutdown()
