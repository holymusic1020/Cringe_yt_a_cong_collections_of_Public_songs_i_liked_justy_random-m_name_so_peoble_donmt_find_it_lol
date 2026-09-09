"""STRICT QA v3 — BACKGROUND-INVARIANT sticker proof.

Compares the FINAL video frame at time T against the RAW bg.mp4 frame at the
SAME time T, inside the sticker zone. diff = exactly the sticker/robot pixels
(bgs can't fake it, motion can't mask it). One speaker per window => the diff
at a speaker's mid-line is THEIR sticker.

Usage: qa_strict.py <video> <timeline.json> [<bg.mp4>]
If bg.mp4 missing (older renders), falls back to v2 frame-diff with a warning.
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

VIDEO = Path(sys.argv[1])
TL = json.loads(Path(sys.argv[2]).read_text())
BG = Path(sys.argv[3]) if len(sys.argv) > 3 else \
    VIDEO.parent / f"{VIDEO.stem}_bg.mp4"
ZONE = (24, 700, 700, 1900)   # sticker/robot zone (below caption area)
THRESH = 0.02                  # 2% strong-diff => sticker present


def grab(src, t, name):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                    "-i", str(src), "-frames:v", "1", name], check=True)
    return Image.open(name).convert("RGB")


def strong_diff(a, b):
    d = ImageChops.difference(a.crop(ZONE), b.crop(ZONE)).convert("L")
    px = list(d.getdata())
    return sum(1 for v in px if v > 40) / len(px)


def main():
    have_bg = BG.exists()
    if not have_bg:
        print("[qa] WARNING: no bg.mp4 — falling back to v2 (less reliable)")
    ref = grab(BG if have_bg else VIDEO, 0.08, "/tmp/qa_ref.png")
    lines = {l["speaker"]: l for l in TL["lines"]}
    failures = []

    def check(sid, label):
        l = lines[sid]
        mid = (l["start"] + l["end"]) / 2
        frame = grab(VIDEO, mid, "/tmp/qa_frame.png")
        if have_bg:
            base = grab(BG, mid, "/tmp/qa_base.png")
        else:
            base = ref
        frac = strong_diff(frame, base)
        ok = frac > THRESH
        print(f"[qa] {label} {sid}: diff {frac*100:.1f}% {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures.append(sid)

    for sid in {l["speaker"] for l in TL["lines"]}:
        if sid in config.HAS_STICKER:
            check(sid, "sticker")
    if config.ROBOT["sid"] in lines:
        check(config.ROBOT["sid"], "robot")

    sp = next(iter(lines.values()))
    im = grab(VIDEO, (sp["start"] + sp["end"]) / 2, "/tmp/qa_cap.png")
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
    print("[qa] ALL BACKGROUND-INVARIANT CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
