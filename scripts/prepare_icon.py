"""Convert the generated PNG to Windows ICO sizes without changing its design."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
with Image.open(root / 'assets' / 'campus-icon.png') as image:
    image.save(root / 'assets' / 'campus.ico', format='ICO',
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
