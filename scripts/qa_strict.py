"""STRICT per-window QA — runs on every GH render (the vanishing-sticker bug
can never come back silently).

Checks (from {video}_timeline.json + the mp4):
1. each stickered speaker: nametag pixels IN window >> OUT window (delta > 300)
2. robot: visor pixels during narrator >> during any other speaker
3. karaoke two-tone present (white highlight + gray upcoming)
exit 1 on any failure -> workflow fails -> boss sees it immediately.
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

VIDEO = Path(sys.argv[1])
TL = json.loads(Path(sys.argv[2]).read_text())
ZONE = (24, 900, 700, 1900)


def grab(t):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                    "-i", str(VIDEO), "-frames:v", "1", "/tmp/qa_s.png"],
                   check=True)
    return Image.open("/tmp/qa_s.png").convert("RGB")


def count(im, box, pred):
    return sum(1 for p in im.crop(box).getdata() if pred(*p))


def main():
    lines = {l["speaker"]: l for l in TL["lines"]}
    failures = []
    for sid in {l["speaker"] for l in TL["lines"]}:
        char = config.CAST[sid]
        if sid not in config.HAS_STICKER:
            continue
        l = lines[sid]
        hexc = char["color"].lstrip("#")
        r0, g0, b0 = tuple(int(hexc[i:i+2], 16) for i in (0, 2, 4))
        mid = (l["start"] + l["end"]) / 2
        inside = count(grab(mid), ZONE,
                       lambda r, g, b: abs(r-r0) < 40 and abs(g-g0) < 40 and abs(b-b0) < 40)
        out_t = 0.5 if abs(0.5 - mid) > 2 else max(0, l["start"] - 1.0)
        outside = count(grab(out_t), ZONE,
                        lambda r, g, b: abs(r-r0) < 40 and abs(g-g0) < 40 and abs(b-b0) < 40)
        good = inside > 500 and (inside - outside) > 300
        print(f"[qa] sticker {sid}: in={inside} out={outside} "
              f"{'PASS' if good else 'FAIL'}")
        if not good:
            failures.append(sid)

    if config.ROBOT["sid"] in lines:
        nl = lines[config.ROBOT["sid"]]
        other = next(l for s, l in lines.items() if s != config.ROBOT["sid"])
        cyan_in = count(grab((nl["start"]+nl["end"])/2), ZONE,
                        lambda r, g, b: r < 120 and g > 150 and b > 150)
        cyan_out = count(grab((other["start"]+other["end"])/2), ZONE,
                         lambda r, g, b: r < 120 and g > 150 and b > 150)
        good = cyan_in > 200 and (cyan_in - cyan_out) > 100
        print(f"[qa] robot visor: narrator={cyan_in} other={cyan_out} "
              f"{'PASS' if good else 'FAIL'}")
        if not good:
            failures.append("robot")

    sp = next(iter(lines.values()))
    im = grab((sp["start"]+sp["end"])/2)
    capbox = (90, 300, 990, 1000)
    white = count(im, capbox, lambda r, g, b: r > 235 and g > 235 and b > 235)
    gray = count(im, capbox, lambda r, g, b: 150 < r < 210 and abs(r-g) < 25
                 and abs(g-b) < 25 and abs(r-b) < 25)
    good = white > 300 and gray > 100
    print(f"[qa] karaoke two-tone: white={white} gray={gray} "
          f"{'PASS' if good else 'FAIL'}")
    if not good:
        failures.append("karaoke")

    if failures:
        print(f"[qa] FAILED: {failures}")
        sys.exit(1)
    print("[qa] ALL STRICT CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
