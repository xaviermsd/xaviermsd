"""Render the profile README visuals to assets/*.png.

    python assets/src/render.py            (needs: pip install playwright imagequant pillow)
    python assets/src/render.py hero.png   (render only the named files)

Every element in visuals.html with a data-out attribute is saved at 2x, then reduced to a
256-colour palette with libimagequant so each file stays small. No text chunks or other
metadata are written to the PNGs.
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
    page = browser.new_page(viewport={'width': 1300, 'height': 8000}, device_scale_factor=2)
    page.goto((HERE / 'visuals.html').as_uri())
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    for el in page.locator('[data-out]').all():
        name = el.get_attribute('data-out')
        if only and name not in only:
            continue
        im = Image.open(io.BytesIO(el.screenshot(omit_background=True))).convert('RGBA')
        q = imagequant.quantize_pil_image(im, dithering_level=0.6, max_colors=256, min_quality=70, max_quality=95)
        path = OUT / name
        q.save(path, optimize=True)
        print(f'{name:22} {im.width}x{im.height}  {path.stat().st_size / 1024:.0f} KB')
    browser.close()
