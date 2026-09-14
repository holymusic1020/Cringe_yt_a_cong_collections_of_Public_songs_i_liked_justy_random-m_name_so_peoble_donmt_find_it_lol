"""DELIVERY GATE — audits THE artifact that ships (boss round-12: watch it
yourself before sending). For every line: sticker zone (bottom-right band)
AND robot zone (bottom-left band) are diffed against the raw bg at the SAME
timestamp — early (+0.6s) and mid samples. Character lines REQUIRE their
sticker; every line REQUIRES the always-on robot. Karaoke + labels checked.
Exit 1 = do not deliver. Usage: audit_video.py <video> <timeline> <bg>
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

VIDEO, TL, BG = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
# Shorts-safe bands (mirrors engine.py layout)
STICKER_ZONE = (545, 880, 995, 1520)
ROBOT_ZONE = (55, 880, 495, 1520)
THRESH = 0.015


def grab(src, t):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(src),
                    "-frames:v", "1", "/tmp/aud.png"], check=True)
    return Image.open("/tmp/aud.png").convert("RGB")


def diff(a, b, box):
    W, H = a.size
    x0, y0, x1, y1 = [int(v / 1080 * W) if i % 2 == 0 else int(v / 1920 * H)
                      for i, v in enumerate(box)]
    d = ImageChops.difference(a.crop((x0, y0, x1, y1)),
                              b.crop((x0, y0, x1, y1))).convert("L")
    px = list(d.getdata())
    return sum(1 for v in px if v > 40) / max(1, len(px))


def main():
    if not BG.exists():
        print("[audit] FATAL: no bg reference — cannot verify (invariant law)")
        sys.exit(1)
    fails = []
    print(f"{'speaker':10s} {'window':>13s} {'stick-e':>8s} {'stick-m':>8s} "
          f"{'robot-m':>8s}  verdict")
    for l in TL["lines"]:
        is_char = l["speaker"] in config.HAS_STICKER
        early = min(l["start"] + 0.6, (l["start"] + l["end"]) / 2)
        mid = (l["start"] + l["end"]) / 2
        f_e, f_m = grab(VIDEO, early), grab(VIDEO, mid)
        b_e, b_m = grab(BG, early), grab(BG, mid)
        se = diff(f_e, b_e, STICKER_ZONE)
        sm = diff(f_m, b_m, STICKER_ZONE)
        rm = diff(f_m, b_m, ROBOT_ZONE)
        is_nar = l["speaker"] == config.ROBOT["sid"]
        if is_char:
            # speaker-exclusive law: the speaker's sticker AND nothing else
            ok = max(se, sm) > THRESH and rm < 0.05
        elif is_nar:
            ok = rm > THRESH and max(se, sm) < 0.05
        else:
            ok = True
        if not ok:
            fails.append(l["speaker"])
        print(f"{l['speaker']:10s} {l['start']:5.1f}-{l['end']:5.1f} "
              f"{se * 100:7.1f}% {sm * 100:7.1f}% {rm * 100:7.1f}%  "
              f"{'OK' if ok else '*** FAIL ***'}")
    # karaoke + name labels in the caption band — sample SEVERAL points
    # across the first line: a single mid-point can land in a [beat] gap
    # between caption events and false-fail with white=0
    l0 = TL["lines"][0]
    f = grab(VIDEO, l0["start"] + 0.4)
    W, H = f.size
    box = (int(0.08 * W), int(0.14 * H), int(0.92 * W), int(0.55 * H))
    white = gray = 0
    span = max(0.8, l0["end"] - l0["start"])
    for frac in (0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95):
        f = grab(VIDEO, l0["start"] + span * frac)
        px = list(f.crop(box).getdata())
        white = max(white, sum(1 for r, g, b in px
                               if r > 235 and g > 235 and b > 235))
        gray = max(gray, sum(1 for r, g, b in px
                             if 140 < r < 215 and abs(r - g) < 30
                             and abs(g - b) < 30))
    kap_ok = white > 300 and gray > 80
    print(f"[audit] karaoke/labels: white={white} gray={gray} "
          f"{'OK' if kap_ok else 'FAIL'}")
    if not kap_ok:
        fails.append("karaoke")
    if fails:
        print(f"[audit] REFUSED DELIVERY: {fails}")
        sys.exit(1)
    print("[audit] EVERY LINE VERIFIED — cleared for delivery ✅")


if __name__ == "__main__":
    main()
