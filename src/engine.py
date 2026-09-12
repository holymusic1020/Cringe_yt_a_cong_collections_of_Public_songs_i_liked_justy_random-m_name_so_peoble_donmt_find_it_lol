"""NixSpeechFav ENGINE v2 — rebuilt from scratch (boss round-12 order).

Design laws (learned from every bug that escaped v1):
 1. ONE ffmpeg command renders everything: bg + all stickers + robot frames
    + captions + voice. No pass chain = no intermediate files, no re-encode
    quality loss, no per-pass state bugs.
 2. Every overlay expression is PURE ARITHMETIC (no ffmpeg `if()`), so the
    EXACT string that ffmpeg evaluates is also valid Python — the engine
    eval()s each expression at 40 timestamps BEFORE rendering and asserts
    positions/enables are sane. A bad expression can never render.
 3. LAYOUT is Shorts-safe: stickers/robot live ABOVE the YouTube Shorts UI
    (bottom title bar ~y1550+, right button rail ~x1010+). v1 put them
    under the UI — viewers literally could not see them.
 4. A 6-second smoke render at half-res runs the REAL expression set and is
    frame-scanned before the full render is allowed to start.
"""
import json, math, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from PIL import Image, ImageChops

# ── Shorts-safe layout (1080x1920) ──────────────────────────────────────
STICKER = {"x": 555, "w": 430, "bottom": 1470}   # right edge 985 < rail
ROBOT = {"x": 65, "w": 420, "bottom": 1470}      # left, above title bar
SLIDE = {"px": 130, "s": 0.24}                    # gentle slide-in
BOB = {"px": 9, "period": 2.8}                    # idle bob
JAW = {"px": 4, "period": 0.16}                   # talk tempo bob

# Python side of the ffmpeg expression functions (validation + docs)
def _fdef():
    def between(t, a, b):
        return 1.0 if a <= t <= b else 0.0
    def lt(a, b): return 1.0 if a < b else 0.0
    def gt(a, b): return 1.0 if a > b else 0.0
    def gte(a, b): return 1.0 if a >= b else 0.0
    def lte(a, b): return 1.0 if a <= b else 0.0
    def _if(c, a, b): return a if c else b
    return {"between": between, "lt": lt, "gt": gt, "gte": gte, "lte": lte,
            "mod": math.fmod, "pow": lambda a, b: float(a) ** float(b),
            "sin": math.sin, "max": max, "min": min, "if": _if, "PI": math.pi}

def _eval(expr, t):
    return eval(expr.strip().strip("'"), {"__builtins__": {}}, {**_fdef(), "t": t})

def _validate(name, expr, samples, lo, hi, want_one_at=()):
    """Assert expr stays within [lo, hi] for all samples and == 1 at the
    timestamps in want_one_at (enable expressions)."""
    for t in samples:
        v = _eval(expr, t)
        assert lo <= v <= hi, f"{name}: {v} at t={t} outside [{lo},{hi}]: {expr}"
    for t in want_one_at:
        v = _eval(expr, t)
        assert v > 0.5, f"{name}: enable={v} at t={t} (should be ON): {expr}"

# ── expression builders (pure arithmetic — Python-evaluable) ────────────
def enable_windows(windows):
    return "+".join(f"between(t,{s:.2f},{e:.2f})" for s, e in windows)

def slide_terms(windows):
    return "".join(
        f"+{SLIDE['px']}*gte(t,{t0:.2f})*"
        f"pow(max(0,1-min(1,(t-{t0:.2f})/{SLIDE['s']})),2)"
        for t0, _ in windows)

def build_overlays(tl):
    """Returns list of dicts: {png, x, w, y_expr, enable_expr} — validated."""
    lines = tl["lines"]
    R = config.ROBOT
    wins = {}   # speaker -> [(s,e)]
    for l in lines:
        wins.setdefault(l["speaker"], []).append((l["start"], l["end"]))
    overlays = []
    H = config.SHORT["h"]
    samples = [i * tl["total_s"] / 40 for i in range(41)]

    # character stickers (bottom-right, Shorts-safe)
    for sid, w in wins.items():
        char = config.CAST.get(sid)
        if char is None or char.get("narrator") or sid not in config.HAS_STICKER:
            continue
        png = config.ASSETS / "stickers" / f"{sid}.png"
        if not png.exists():
            continue
        h_px = int(Image.open(png).size[1] * STICKER["w"] / Image.open(png).size[0])
        y0 = STICKER["bottom"] - h_px
        en = enable_windows(w)
        y = f"{y0}{slide_terms(w)}"
        _validate(f"y[{sid}]", y, samples, y0 - 1, y0 + SLIDE["px"] + 1)
        _validate(f"en[{sid}]", en, samples, -0.1, len(w) + 0.1,
                  want_one_at=[(s + e) / 2 for s, e in w])
        overlays.append({"png": str(png), "x": STICKER["x"], "w": STICKER["w"],
                         "y": y, "en": en, "who": sid,
                         "until": max(e for _, e in w)})

    # robot (bottom-left, ALWAYS on): base / antenna-vibrate / blink
    rwins = wins.get(R["sid"], [])
    talk = enable_windows(rwins) if rwins else "0"
    talk = f"gt({talk},0.5)" if rwins else "0"
    blink = f"lt(mod(t,{R['blink_period_s']}),{R['blink_dur_s']})"
    flicker = f"lt(mod(t,{R['talk_flicker_period_s']}),{R['talk_flicker_on_s']})"
    rpng = config.ASSETS / "robot_keyed" / "robot.png"
    h_px = int(Image.open(rpng).size[1] * ROBOT["w"] / Image.open(rpng).size[0])
    y0 = ROBOT["bottom"] - h_px
    y = (f"{y0}+{BOB['px']}*sin(2*PI*t/{BOB['period']})"
         f"+{JAW['px']}*sin(2*PI*t/{JAW['period']})*({talk})"
         + slide_terms(rwins))
    base_en = f"(1-{blink})*(1-{talk}*{flicker})"
    ant_en = f"{talk}*{flicker}*(1-{blink})"
    blink_en = blink
    _validate("y[robot]", y, samples, y0 - BOB["px"] - 2,
              y0 + BOB["px"] + SLIDE["px"] + 2)
    for nm, ex in (("base", base_en), ("antenna", ant_en), ("blink", blink_en)):
        _validate(f"en[robot-{nm}]", ex, samples, -0.1, 1.1)
    # robot must be visible (some frame) at every sample: base+ant+blink == 1
    for t in samples:
        tot = (_eval(base_en, t) + _eval(ant_en, t) + _eval(blink_en, t))
        assert 0.9 < tot < 1.1, f"robot frame gap at t={t}: {tot}"
    overlays.append({"png": str(rpng), "x": ROBOT["x"], "w": ROBOT["w"],
                     "y": y, "en": base_en, "who": "robot"})
    overlays.append({"png": str(config.ASSETS / "robot_keyed" / "robot_antenna.png"),
                     "x": ROBOT["x"], "w": ROBOT["w"], "y": y, "en": ant_en,
                     "who": "robot_antenna"})
    overlays.append({"png": str(config.ASSETS / "robot_keyed" / "robot_blink.png"),
                     "x": ROBOT["x"], "w": ROBOT["w"], "y": "min(" + y + "," + str(ROBOT["bottom"] - 10) + ")",
                     "en": blink_en, "who": "robot_blink"})
    return overlays


def _ffmpeg(overlays, bg, caps, voice, out, total, scale=1.0, t_limit=None,
            threads=2):
    """Build + run the ONE-PASS render command."""
    H, W = config.SHORT["h"], config.SHORT["w"]
    if scale != 1.0:
        W, H = int(W * scale), int(H * scale)
    cmd = ["ffmpeg", "-y", "-nostdin", "-i", str(bg)]
    for o in overlays:
        # memory law (attempt e OOM): cap each looped input to its active
        # window (+lead). overlay's default eof_action=repeat holds the last
        # frame and enable=0 hides it anyway — visually identical, but the
        # filtergraph queues stay small (11 full-span inputs hit 1.5GB).
        span = total if o.get("until") is None else min(o["until"] + 1.5, total)
        if t_limit is not None:
            span = min(span, t_limit + 0.5)
        cmd += ["-loop", "1", "-r", str(config.SHORT["fps"]),
                "-t", f"{span:.2f}", "-i", o["png"]]
    cmd += ["-i", str(voice)]
    parts = []
    if scale != 1.0:
        # true half-res graph: downscale the canvas FIRST so every overlay
        # coord is in half-res units. (attempt-e bug: x/size were pre-halved
        # but pasted on the FULL-res base and then halved again by the final
        # scale — sticker landed left of its scan zone; y was the only coord
        # scaled once, by accident.)
        parts.append(f"[0:v]scale={W}:{H}[base]")
        prev = "[base]"
    else:
        prev = "[0:v]"   # explicit — never rely on ffmpeg's label fallback
    for i, o in enumerate(overlays):
        x = int(o["x"] * scale)
        y = o["y"] if scale == 1.0 else f"({o['y']})*{scale}"
        cmd_in = f"[{i + 1}:v]scale={int(o['w'] * scale)}:-2,format=rgba[s{i}]"
        nxt = f"[v{i}]"
        parts.append(f"{cmd_in};"
                     f"{prev}[s{i}]overlay=x={x}:y='{y}':"
                     f"enable='{o['en']}':eval=frame{nxt}")
        prev = nxt
    parts.append(f"{prev}scale={W}:{H},"
                 f"ass=filename='{caps}':fontsdir='{config.ASSETS / 'fonts'}',"
                 f"format=yuv420p[vout]")
    cmd += ["-filter_complex", ";".join(parts),
            "-map", "[vout]", "-map", f"{len(overlays) + 1}:a",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-c:v", "libx264", "-preset", config.X264["preset"],
            "-threads", str(threads), "-crf", config.X264["crf"],
            "-r", str(config.SHORT["fps"]),
            "-movflags", "+faststart"]
    if t_limit:
        cmd += ["-t", f"{t_limit:.2f}"]
    cmd += ["-shortest", str(out)]
    return cmd


def _grab(video, t):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(video),
                    "-frames:v", "1", "/tmp/eng_scan.png"], check=True)
    return Image.open("/tmp/eng_scan.png").convert("RGB")


def _zone_changed(a, b, box):
    """Fraction of zone pixels differing >40 vs the raw bg — same metric as
    the delivery gate (audit_video.py); color-agnostic, so dark-palette
    stickers can't false-fail the way white-scans did."""
    W, H = a.size
    x0, y0, x1, y1 = [int(v / 1080 * W) if i % 2 == 0 else int(v / 1920 * H)
                      for i, v in enumerate(box)]
    d = ImageChops.difference(a.crop((x0, y0, x1, y1)),
                              b.crop((x0, y0, x1, y1))).convert("L")
    px = list(d.getdata())
    return sum(1 for v in px if v > 40) / max(1, len(px))


def _active_overlays(overlays, t_end):
    """Overlays actually ON during [0, t_end] — the smoke graph only needs
    these (robot trio is always-on by the frame-sum invariant)."""
    keep = [o for o in overlays if o["who"].startswith("robot")]
    for o in overlays:
        if not o["who"].startswith("robot"):
            if any(_eval(o["en"], i * t_end / 30) > 0.5 for i in range(31)):
                keep.append(o)
    return keep


def smoke_render(overlays, bg, caps, voice, workdir, first_line):
    """6s half-res render of the REAL expressions; frame-assert stickers."""
    t_end = min(6.0, first_line["end"])
    act = _active_overlays(overlays, t_end)
    print(f"[engine] smoke graph: {len(act)}/{len(overlays)} overlays "
          f"active in first {t_end:.1f}s")
    out = workdir / "smoke.mp4"
    cmd = _ffmpeg(act, bg, caps, voice, out, t_end, scale=0.5,
                  t_limit=t_end)
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, f"smoke render failed rc={p.returncode}: {p.stderr[-600:]}"
    # first line is always a character hook (script law) — sticker + robot
    # must both be visible in the Shorts-safe band (diff vs raw bg, same
    # metric as the delivery gate)
    mid = min(2.2, (first_line["start"] + first_line["end"]) / 2)
    sm = _grab(out, mid)
    bgr = _grab(bg, mid)
    if bgr.size != sm.size:
        bgr = bgr.resize(sm.size)
    s = _zone_changed(sm, bgr, (STICKER["x"], 900, STICKER["x"] + STICKER["w"], 1520))
    r = _zone_changed(sm, bgr, (ROBOT["x"], 900, ROBOT["x"] + ROBOT["w"], 1520))
    assert s > 0.015, f"smoke: sticker not visible at t={mid} ({s * 100:.1f}% changed)"
    assert r > 0.015, f"smoke: robot not visible at t={mid} ({r * 100:.1f}% changed)"
    out.unlink(missing_ok=True)
    return True


def render(workdir, out_path):
    """Full pipeline: validate -> smoke -> one-pass render."""
    tl = json.loads((workdir / "timeline.json").read_text())
    total = tl["total_s"]
    overlays = build_overlays(tl)
    print(f"[engine] {len(overlays)} overlays built + validated "
          f"(expressions eval'd at 41 timestamps each)")
    first = tl["lines"][0]
    smoke_render(overlays, workdir / "bg.mp4", workdir / "captions.ass",
                 workdir / "voice.mp3", workdir, first)
    print("[engine] smoke render PASSED (sticker+robot visible in band)")
    t0 = time.time()
    cmd = _ffmpeg(overlays, workdir / "bg.mp4", workdir / "captions.ass",
                  workdir / "voice.mp3", out_path, total)
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, f"render failed rc={p.returncode}: {p.stderr[-800:]}"
    print(f"[engine] one-pass render done in {time.time() - t0:.0f}s "
          f"-> {out_path.name} ({total:.1f}s, {len(overlays)} overlays)")


if __name__ == "__main__":
    render(Path(sys.argv[1]), Path(sys.argv[2]))
