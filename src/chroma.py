"""Chroma-key raw green-screen stickers -> transparent PNGs (reusable in CI)."""
import sys, os
from PIL import Image

def green_frac(im, step=8):
    w, h = im.size; n = g = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, gr, b = im.getpixel((x, y))[:3]; n += 1
            if gr > 120 and gr > r * 1.35 and gr > b * 1.35: g += 1
    return g / n

def key(im, thresh=1.25):
    """Distance-to-pure-green keying with soft feather edge."""
    im = im.convert("RGBA"); w, h = im.size
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            # greenness ratio: green channel dominance
            if g > 90 and g > r * thresh and g > b * thresh:
                # feather: stronger dominance -> fully transparent
                dom = min(g / max(r, 1), g / max(b, 1))
                alpha = 0 if dom > 1.6 else int(255 * (dom - thresh) / (1.6 - thresh))
                px[x, y] = (r, g, b, min(a, alpha))
    return im

def autocrop(im):
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    im = Image.open(src).convert("RGB")
    frac = green_frac(im)
    ok = frac > 0.20  # bust portrait should have 20%+ bg
    keyed = autocrop(key(im))
    keyed.save(dst)
    # alpha coverage sanity: character should cover 30-80% of cropped canvas
    a = keyed.getchannel("A"); w, h = keyed.size
    hist = a.histogram()  # 256 bins; alpha>128 = bins 129..255
    solid = sum(hist[129:]) / (w * h)
    print(f"{os.path.basename(src)}: bg_green={frac:.2f} keyed_size={w}x{h} solid={solid:.2f} {'OK' if ok and 0.25 <= solid <= 0.95 else 'CHECK!'}")
