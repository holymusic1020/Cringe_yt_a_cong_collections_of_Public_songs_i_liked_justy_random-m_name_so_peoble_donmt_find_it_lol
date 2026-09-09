#!/usr/bin/env python3
"""Rebuild every character sticker: key (if raw) -> white-outline stickerize.
Existing keyed PNGs get outlined in place; new raws get keyed first.
"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from chroma import key
from stickers import stickerize

RAW = ROOT / "assets" / "raw"
STK = ROOT / "assets" / "stickers"
STK.mkdir(parents=True, exist_ok=True)

count = 0
for raw in sorted(RAW.glob("*.png")):
    stem = raw.stem
    keyed = key(Image.open(raw).convert("RGB"))
    stickerize(keyed).save(STK / f"{stem}.png")
    print(f"{stem}: raw keyed + stickerized")
    count += 1

for keyed_png in sorted(STK.glob("*.png")):
    if (RAW / keyed_png.name).exists():
        continue  # just rebuilt above
    stickerize(Image.open(keyed_png)).save(keyed_png)
    print(f"{keyed_png.stem}: outlined in place")
    count += 1

print(f"done: {count} stickers in {STK}")
