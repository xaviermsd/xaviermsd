"""Render the project banners in banners.html to assets/*.jpg.

    python assets/src/render_banners.py                 (all)
    python assets/src/render_banners.py banner-ronin.jpg

Each .bn element is shot at 1.5x (2400x960) and saved as a progressive JPEG with no metadata.
"""
import io, pathlib, sys
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
only = set(sys.argv[1:])

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1700, 'height': 2400}, device_scale_factor=1.5)
    page.goto((HERE / 'banners.html').as_uri())
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    for el in page.locator('[data-out]').all():
        name = el.get_attribute('data-out')
        if only and name not in only:
            continue
        im = Image.open(io.BytesIO(el.screenshot())).convert('RGB')
        path = OUT / name
        im.save(path, quality=88, optimize=True, progressive=True)
        print(f'{name:24} {im.width}x{im.height}  {path.stat().st_size / 1024:.0f} KB')
    browser.close()
