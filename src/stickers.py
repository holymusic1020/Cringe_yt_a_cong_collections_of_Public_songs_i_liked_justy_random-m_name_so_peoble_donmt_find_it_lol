"""Sticker factory: keyed PNG -> white-outline sticker with soft drop shadow.

The classic 'sticker look' (boss request): thick white border so characters
pop against ANY background + soft shadow for depth.
"""
from PIL import Image, ImageFilter


def stickerize(im, outline=7, shadow_alpha=110, shadow_blur=12, offset=(8, 14)):
    """RGBA keyed image -> outlined sticker (deterministic: same input layout
    always gets the same outline, so animation frames stay aligned)."""
    im = im.convert("RGBA")
    a = im.getchannel("A")
    dil = a.filter(ImageFilter.MaxFilter(outline * 2 + 1))
    empty = Image.new("RGBA", im.size, (0, 0, 0, 0))

    # white border layer (border = dilated alpha, painted white)
    white = Image.new("RGBA", im.size, (255, 255, 255, 255))
    base = Image.composite(white, empty, dil)

    # soft drop shadow (blurred dilated alpha, offset)
    sh = dil.filter(ImageFilter.GaussianBlur(shadow_blur))
    black = Image.new("RGBA", im.size, (0, 0, 0, shadow_alpha))
    shadow = Image.composite(black, empty, sh)

    pad_x, pad_y = abs(offset[0]) + shadow_blur, abs(offset[1]) + shadow_blur
    canvas = Image.new("RGBA",
                       (im.width + pad_x * 2, im.height + pad_y * 2),
                       (0, 0, 0, 0))
    canvas.alpha_composite(shadow, (pad_x + offset[0], pad_y + offset[1]))
    canvas.alpha_composite(base, (pad_x, pad_y))
    canvas.alpha_composite(im, (pad_x, pad_y))
    bbox = canvas.getchannel("A").getbbox()
    return canvas.crop(bbox)
