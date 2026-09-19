"""Resolve read-only assets in both a checkout and a PyInstaller bundle."""
from pathlib import Path
import sys


def asset_path(name):
    root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    return root / 'assets' / name
