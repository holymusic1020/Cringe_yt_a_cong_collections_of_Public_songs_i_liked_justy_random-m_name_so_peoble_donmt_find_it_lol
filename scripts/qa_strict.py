"""STRICT QA v2 — FRAME-DIFF based (color counting was fooled by colorful bg).

Method: t≈0.08s is a clean reference (slide-ins still offscreen, zone empty).
Each stickered speaker's mid-window frame vs reference: strong-diff fraction
in the sticker zone must exceed threshold => sticker actually rendered.
Same for the robot visor zone during narrator lines. Exits 1 on failure.
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

VIDEO = Path(sys.argv[1])
TL = json.loads(Path(sys.argv[2]).read_text())
ZONE = (24, 900, 700, 1900)          # sticker+robot zone
REF_T = 0.08                          # before any slide-in completes
THRESH = 0.10                         # strong-diff fraction => sticker present


def grab(t):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                    "-i", str(VIDEO), "-frames:v", "1", "/tmp/qa_v2.png"],
                   check=True)
    return Image.open("/tmp/qa_v2.png").convert("RGB")


def strong_diff(a, b):
    d = ImageChops.difference(a.crop(ZONE), b.crop(ZONE)).convert("L")
    px = list(d.getdata())
    return sum(1 for v in px if v > 40) / len(px)


def main():
    ref = grab(REF_T)
    lines = {l["speaker"]: l for l in TL["lines"]}
    failures = []

    for sid in {l["speaker"] for l in TL["lines"]}:
        if sid not in config.HAS_STICKER:
            continue
        l = lines[sid]
        frac = strong_diff(grab((l["start"] + l["end"]) / 2), ref)
        ok = frac > THRESH
        print(f"[qa] sticker {sid}: zone-diff {frac*100:.1f}% "
              f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            failures.append(sid)

    if config.ROBOT["sid"] in lines:
        l = lines[config.ROBOT["sid"]]
        frac = strong_diff(grab((l["start"] + l["end"]) / 2), ref)
        ok = frac > THRESH
        print(f"[qa] robot: zone-diff {frac*100:.1f}% {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures.append("robot")

    sp = next(iter(lines.values()))
    im = grab((sp["start"] + sp["end"]) / 2)
    capbox = (90, 300, 990, 1000)
    px = list(im.crop(capbox).getdata())
    white = sum(1 for r, g, b in px if r > 235 and g > 235 and b > 235)
    gray = sum(1 for r, g, b in px if 150 < r < 210 and abs(r - g) < 25
               and abs(g - b) < 25 and abs(r - b) < 25)
    ok = white > 300 and gray > 100
    print(f"[qa] karaoke two-tone: white={white} gray={gray} "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("karaoke")

    if failures:
        print(f"[qa] FAILED: {failures}")
        sys.exit(1)
    print("[qa] ALL FRAME-DIFF CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
