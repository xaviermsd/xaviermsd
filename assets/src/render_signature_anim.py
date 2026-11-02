"""Render the animated email signature images from signature.html to assets/signature/*.gif.

    python assets/src/render_signature_anim.py

cta.gif:      the dot pulses and the arrow nudges right, 2.4 s loop.
<icon>.gif:   the social chips lift one after another in a wave, then rest, 4 s loop.

Frame one is the resting state, because Outlook classic on Windows shows only the first frame. GIF has no soft
transparency, so edge pixels are blended into ink (every outer edge here is an ink border or ink shadow) and the rest is
cut out. All frames share one palette and identical frames are merged.
"""
import io, math, pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / 'signature'
INK = (8, 8, 8)
ICONS = ['linkedin', 'github', 'youtube', 'instagram', 'wordpress']


def shoot(el):
    return Image.open(io.BytesIO(el.screenshot(omit_background=True))).convert('RGBA')


def save_gif(path, frames, disposal=2):
    """frames: list of (RGBA image, ms). Merges repeats, shares one palette, index 255 is transparent.
    disposal=1 stores only what changed, which is safe only when the moving parts never cross a transparent area."""
    merged = []
    for im, ms in frames:
        if merged and merged[-1][0].tobytes() == im.tobytes():
            merged[-1][1] += ms
        else:
            merged.append([im, ms])
    flat = []
    for im, _ in merged:
        rgb = Image.new('RGB', im.size, INK)
        rgb.paste(im.convert('RGB'), mask=im.getchannel('A'))
        flat.append((rgb, im.getchannel('A').point(lambda a: 255 if a < 110 else 0)))
    w, h = flat[0][0].size
    sheet = Image.new('RGB', (w, h * len(flat)))
    for i, (rgb, _) in enumerate(flat):
        sheet.paste(rgb, (0, h * i))
    pal = sheet.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for rgb, cut in flat:
        p = rgb.quantize(palette=pal, dither=Image.Dither.NONE)
        p.paste(255, mask=cut)
        out.append(p)
    out[0].save(path, save_all=True, append_images=out[1:], duration=[ms for _, ms in merged], loop=0,
                transparency=255, disposal=disposal, optimize=False)
    print(f'{path.name:16} {w}x{h}  {len(out)} frames  {path.stat().st_size / 1024:.0f} KB')


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 800, 'height': 600}, device_scale_factor=2)
    page.goto((HERE / 'signature.html').as_uri())
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')

    # button: two pulses of the dot per loop, one arrow nudge at the start
    cta = page.locator('[data-out="signature/cta.png"]')
    frames = []
    for t in range(0, 2400, 100):
        k = (t % 1200) / 1200
        ring, alpha = 2 + 6 * k, 0.35 * (1 - k)
        nudge = 4 * math.sin(math.pi * t / 600) if t < 600 else 0
        page.evaluate(f'''() => {{
            document.querySelector('.cta .dot').style.boxShadow = '0 0 0 {ring:.2f}px rgba(8,8,8,{alpha:.3f})';
            document.querySelector('.cta svg').style.transform = 'translateX({nudge:.2f}px)';
        }}''')
        frames.append((shoot(cta), 100))
    save_gif(OUT / 'cta.gif', frames, disposal=1)  # dot and arrow stay inside the pill

    # chips: 37 x 37 canvas, chip rests 3px in from the top left and lifts to 0 while its shadow stays put
    page.add_style_tag(content='.chip { width: 37px; height: 37px; } .chip i { left: 6px; top: 6px; } .chip b { left: 3px; top: 3px; }')
    for n, name in enumerate(ICONS):
        chip = page.locator(f'[data-out="signature/{name}.png"]')
        start, frames = 200 + n * 140, []
        for t in range(0, 1600, 40):
            u = (t - start) / 400
            lift = math.sin(math.pi * u) if 0 <= u <= 1 else 0
            page.evaluate(f'''() => {{ const b = document.querySelector('[data-out="signature/{name}.png"] b');
                b.style.left = b.style.top = '{3 - 3 * lift:.2f}px'; }}''')
            frames.append((shoot(chip), 40))
        frames[-1] = (frames[-1][0], 40 + 2400)
        save_gif(OUT / f'{name}.gif', frames)
    browser.close()
