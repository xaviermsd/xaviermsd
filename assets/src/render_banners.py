"""Render the featured project banners in banners.html to assets/banner-*.png.

    python assets/src/render_banners.py                    (all)
    python assets/src/render_banners.py banner-ronin.png   (only the named files)

Each .bw element is shot at 1.5x with a transparent background (the frame has round corners and a hard offset
shadow), then reduced to a 256-colour palette with libimagequant so the files stay small. No metadata is written.
"""
import io, pathlib, sys
import imagequant
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
only = set(sys.argv[1:])

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1700, 'height': 4600}, device_scale_factor=1.5)
    page.goto((HERE / 'banners.html').as_uri())
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    for el in page.locator('[data-out]').all():
        name = el.get_attribute('data-out')
        if only and name not in only:
            continue
        im = Image.open(io.BytesIO(el.screenshot(omit_background=True))).convert('RGBA')
        q = imagequant.quantize_pil_image(im, dithering_level=0.8, max_colors=256, min_quality=75, max_quality=98)
        path = OUT / name
        q.save(path, optimize=True)
        print(f'{name:24} {im.width}x{im.height}  {path.stat().st_size / 1024:.0f} KB')
    browser.close()
