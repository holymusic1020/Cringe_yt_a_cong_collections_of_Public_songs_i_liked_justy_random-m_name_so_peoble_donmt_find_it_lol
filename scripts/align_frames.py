"""Align robot frames to a shared canvas (union bbox) so the flicker animation
only moves the antenna — head stays pixel-still."""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config  # noqa: F401  (paths)
from chroma import key

RAW = config.ASSETS / "robot"
OUT = config.ASSETS / "robot_keyed"
FRAMES = ["robot", "robot_blink", "robot_antenna"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    imgs = {}
    for f in FRAMES:
        im = Image.open(RAW / f"{f}_raw.png").convert("RGB")
        imgs[f] = key(im)  # keyed, uncropped (full canvas)

    # union bbox across all frames
    boxes = [im.getchannel("A").getbbox() for im in imgs.values()]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    for f, im in imgs.items():
        im.crop(box).save(OUT / f"{f}.png")
        print(f"{f}: {im.size} -> union crop {box} -> {(box[2]-box[0], box[3]-box[1])}")
    print("all frames share identical canvas ✅")


if __name__ == "__main__":
    main()
