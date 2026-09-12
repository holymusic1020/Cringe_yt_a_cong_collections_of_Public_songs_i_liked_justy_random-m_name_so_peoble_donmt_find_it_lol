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
# stickers live bottom-RIGHT (x 496-1056), robot bottom-LEFT (x 24-624) —
# separate zones or the always-on robot false-passes every sticker check
STICKER_ZONE = (500, 900, 1060, 1900)
ROBOT_ZONE = (24, 900, 700, 1900)
THRESH = 0.02                  # 2% strong-diff => present


def grab(src, t, name):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                    "-i", str(src), "-frames:v", "1", name], check=True)
    return Image.open(name).convert("RGB")


def strong_diff(a, b, zone):
    d = ImageChops.difference(a.crop(zone), b.crop(zone)).convert("L")
    px = list(d.getdata())
    return sum(1 for v in px if v > 40) / len(px)


def main():
    have_bg = BG.exists()
    if not have_bg:
        print("[qa] WARNING: no bg.mp4 — falling back to v2 (less reliable)")
    ref = grab(BG if have_bg else VIDEO, 0.08, "/tmp/qa_ref.png")
    lines = {l["speaker"]: l for l in TL["lines"]}
    failures = []

    def check(sid, label, zone):
        # sample BOTH the line start (+0.6s, catches slide/enable bugs that
        # hide early lines) and the middle — the strongest frame counts
        l = lines[sid]
        best = 0.0
        for t in (l["start"] + 0.6, (l["start"] + l["end"]) / 2):
            if t >= l["end"]:
                continue
            frame = grab(VIDEO, t, "/tmp/qa_frame.png")
            base = grab(BG, t, "/tmp/qa_base.png") if have_bg else ref
            best = max(best, strong_diff(frame, base, zone))
        ok = best > THRESH
        print(f"[qa] {label} {sid}: diff {best*100:.1f}% {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures.append(sid)

    for sid in {l["speaker"] for l in TL["lines"]}:
        if sid in config.HAS_STICKER:
            check(sid, "sticker", STICKER_ZONE)
    if config.ROBOT["sid"] in lines:
        # robot must be on screen during a NON-narrator line too (always-on)
        other = next((l for l in TL["lines"]
                      if l["speaker"] != config.ROBOT["sid"]), None)
        if other:
            frame = grab(VIDEO, (other["start"] + other["end"]) / 2,
                         "/tmp/qa_frame.png")
            base = (grab(BG, (other["start"] + other["end"]) / 2, "/tmp/qa_base.png")
                    if have_bg else ref)
            frac = strong_diff(frame, base, ROBOT_ZONE)
            ok = frac > THRESH
            print(f"[qa] robot (during {other['speaker']}): "
                  f"{frac*100:.1f}% {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures.append("robot-always-on")
        check(config.ROBOT["sid"], "robot", ROBOT_ZONE)

    # karaoke: sample several caption frames (a [beat] pause can leave the
    # sampled frame mid-gap) and judge the strongest frame
    capbox = (90, 300, 990, 1000)
    best_w = best_g = 0
    for l in TL["lines"][:3]:
        for t in ((l["start"] + l["end"]) / 2,
                  l["start"] + (l["end"] - l["start"]) * 0.3):
            im = grab(VIDEO, t, "/tmp/qa_cap.png")
            px = list(im.crop(capbox).getdata())
            w = sum(1 for r, g, b in px if r > 235 and g > 235 and b > 235)
            g = sum(1 for r, g, b in px if 150 < r < 210 and abs(r - g) < 25
                    and abs(g - b) < 25 and abs(r - b) < 25)
            if w + g > best_w + best_g:
                best_w, best_g = w, g
    ok = best_w > 300 and best_g > 100
    print(f"[qa] karaoke two-tone: white={best_w} gray={best_g} "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append("karaoke")

    if failures:
        print(f"[qa] FAILED: {failures}")
        sys.exit(1)
    print("[qa] ALL BACKGROUND-INVARIANT CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
