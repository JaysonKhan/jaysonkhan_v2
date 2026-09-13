"""Downscale/export selected Imagegen PNGs without altering generated artwork.

No background removal, recoloring or image synthesis: alpha comes from Imagegen.
Run using the repository virtualenv (Pillow). Solar SVGs/fonts are vendored.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'jaysonkhan_mail/assets'


def source(name):
    img = Image.open(ROOT / 'artwork' / name)
    if img.mode != 'RGBA' or img.getextrema()[3][0] != 0:
        raise ValueError(f'{name} must have genuine generated transparency')
    return img


def main():
    mark = source('mark-v1.png')
    for name, size in [('icon.png', 256), ('logo.png', 256), ('favicon-jayson-v1.png', 64)]:
        mark.resize((size, size), Image.Resampling.LANCZOS).save(ASSETS / name, optimize=True)
    for name in ['mail-empty-v1', 'contacts-empty-v1']:
        image = source(name + '.png')
        image.thumbnail((400, 400), Image.Resampling.LANCZOS)
        image.save(ASSETS / (name + '.webp'), quality=88, method=6)
    print('Transparent web exports regenerated; originals preserved.')


if __name__ == '__main__':
    main()
