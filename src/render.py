"""Final compose: bg + karaoke captions + ANIMATED sticker pop-ins + voice.

Animations (boss spec):
- every sticker SLIDES IN from below on each speaking window (fast, eased)
- the ROBOT narrator: idle bob (sine) + periodic blink (frame swap) + slide-in

Layout (1080x1920): captions TOP multi-line, stickers bottom-left.
Sequential light passes (2GB-runner friendly) + OOM-resilient retries.
Final output gets +faststart so browser previews never stall.
"""
import gc, json, os, shutil, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ROBOT_DIR = config.ASSETS / "robot_keyed"


def _run(cmd, timeout=1500):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({p.returncode}): {p.stderr[-1200:]}")
    return p


def _drop_caches():
    for c in (["sudo", "-n", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
              ["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"]):
        try:
            if subprocess.run(c, capture_output=True, timeout=15).returncode == 0:
                print("[render] page cache dropped"); return
        except Exception:
            pass


def _run_resilient(cmd, timeout=1500, tries=3, cool=15):
    """Retry on SIGKILL (-9): transient sandbox memory pressure."""
    for attempt in range(1, tries + 1):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0:
            return p
        if p.returncode == -9 and attempt < tries:
            print(f"[render] pass killed (OOM pressure) attempt {attempt}/{tries} "
                  f"— cooling {cool}s and retrying")
            _drop_caches(); time.sleep(cool); cool *= 2
            continue
        raise RuntimeError(f"ffmpeg failed ({p.returncode}): {p.stderr[-1200:]}")


def bake_nametag(sid, out_path):
    """sticker + rounded name-tag bar in speaker color."""
    char = config.CAST[sid]
    src = config.ASSETS / "stickers" / f"{sid}.png"
    im = Image.open(src).convert("RGBA")
    tag_h = 92
    canvas = Image.new("RGBA", (im.width, im.height + tag_h), (0, 0, 0, 0))
    canvas.paste(im, (0, 0), im)
    color = tuple(int(char["color"][i:i + 2], 16) for i in (1, 3, 5))
    bar = Image.new("RGBA", (im.width, tag_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    bd.rounded_rectangle([4, 6, im.width - 4, tag_h - 6], radius=28,
                         fill=color + (255,))
    name = char["name"].split(" (")[0]
    font = ImageFont.truetype(FONT_BOLD, 46)
    tw = bd.textlength(name, font=font)
    bd.text(((im.width - tw) / 2, 18), name, font=font, fill=(255, 255, 255, 255))
    canvas.paste(bar, (0, im.height), bar)
    canvas.save(out_path)
    return out_path


def _slide_terms(windows, R):
    """ffmpeg expr terms: eased slide-in offset decaying to 0 after slide_s.
    NOTE: plain commas — argv is passed without a shell, and escaped commas
    made the expr parser silently mis-evaluate (the vanishing-sticker bug)."""
    s, dur = R["slide_px"], R["slide_s"]
    terms = []
    for t0, _ in windows:
        terms.append(
            f"{s}*pow(max(0,1-min(1,(t-{t0:.2f})/{dur})),2)")
    return terms


def _enable_expr(windows):
    return "+".join(f"between(t,{s:.2f},{e:.2f})" for s, e in windows)


def render(workdir, out_path):
    workdir = Path(workdir)
    tl = json.loads((workdir / "timeline.json").read_text())
    total = tl["total_s"]
    bg, voice, caps = workdir / "bg.mp4", workdir / "voice.mp3", workdir / "captions.ass"

    windows = {}
    for line in tl["lines"]:
        windows.setdefault(line["speaker"], []).append((line["start"], line["end"]))

    R = config.ROBOT
    has_robot = R["sid"] in windows
    sticker_sids = [s for s in windows
                    if s in config.HAS_STICKER][:config.LAYOUT["max_sticker_passes"]]

    # ── Pass A: bg + karaoke captions
    tmp = workdir / "tmp_capped.mp4"
    _run_resilient(["ffmpeg", "-y", "-nostdin", "-i", str(bg),
          "-vf", f"ass=filename='{caps}':fontsdir='{config.ASSETS / 'fonts'}',format=yuv420p",
          "-t", f"{total:.2f}", "-r", str(config.SHORT["fps"]),
          "-c:v", "libx264", "-preset", config.X264["preset"],
          "-crf", config.X264["crf"], "-an", str(tmp)])
    bg.unlink(missing_ok=True)
    for f in workdir.glob("line_*.mp3"):
        f.unlink(missing_ok=True)
    for f in workdir.glob("bg_raw*"):
        f.unlink(missing_ok=True)
    _drop_caches()

    def pos_for(png, w):
        w0, h0 = Image.open(png).size
        h_scaled = int(h0 * w / w0)
        return h_scaled

    # ── Pass B chain: one overlay per pass
    def overlay_pass(cur, nxt, png, w, x, y_expr, enable_expr, last, voice_in=False):
        cmd = ["ffmpeg", "-y", "-nostdin",
               "-i", str(cur),
               "-loop", "1", "-r", str(config.SHORT["fps"]),
               "-t", f"{total:.2f}", "-i", str(png)]
        if last:
            cmd += ["-i", str(voice)]
        cmd += ["-filter_complex",
                f"[1:v]scale={w}:-2,format=rgba[stk];"
                f"[0:v][stk]overlay=x={x}:y='{y_expr}':"
                f"enable='{enable_expr}':eval=frame,format=yuv420p[vout]",
                "-map", "[vout]"]
        if last:
            cmd += ["-map", "2:a", "-c:a", "aac", "-ar", "44100",
                    "-b:a", "128k", "-shortest", "-movflags", "+faststart"]
        cmd += ["-t", f"{total:.2f}", "-r", str(config.SHORT["fps"]),
                "-c:v", "libx264", "-preset", config.X264["preset"],
                "-crf", "16" if not last else config.X264["crf"]]
        cmd.append(str(nxt))
        _run_resilient(cmd)

    cur = tmp
    passes = []

    # character stickers: slide-in on every speaking window
    for sid in sticker_sids:
        tagged = bake_nametag(sid, workdir / f"tagged_{sid}.png")
        h_scaled = pos_for(tagged, config.LAYOUT["sticker_w"])
        sy = config.SHORT["h"] - config.LAYOUT["sticker_bottom_gap"] - h_scaled
        y_expr = str(sy) + "".join("+" + t for t in _slide_terms(windows[sid], R))
        passes.append((tagged, config.LAYOUT["sticker_w"],
                       config.LAYOUT["sticker_x"], y_expr,
                       _enable_expr(windows[sid])))

    # robot narrator: bob + slide + blink + ANTENNA VIBRATION while talking
    # (3-frame system: open / antenna-tilt / blink — flicker = vibration)
    if has_robot:
        w = windows[R["sid"]]
        h_scaled = pos_for(ROBOT_DIR / "robot.png", R["w"])
        base_y = config.SHORT["h"] - R["bottom_gap"] - h_scaled
        bob = (f"{base_y}+{R['bob_px']}*sin(2*PI*t/{R['bob_period_s']})")
        talk = _enable_expr(w)
        # JAW MOTION (boss spec): no visible mouth — while talking, the whole
        # head bobs slightly at speech tempo = "his jaw is moving"
        jaw = (f"{R['jaw_bob_px']}*sin(2*PI*t/{R['jaw_bob_period_s']})*({talk})")
        y_expr = bob + "+" + jaw + "".join("+" + t for t in _slide_terms(w, R))
        flicker = (f"lt(mod(t,{R['talk_flicker_period_s']}),"
                   f"{R['talk_flicker_on_s']})")
        blink = f"lt(mod(t,{R['blink_period_s']}),{R['blink_dur_s']})"
        passes.append((ROBOT_DIR / "robot.png", R["w"], R["x"], y_expr,
                       f"if({talk},if({flicker},0,if({blink},0,1)),0)"))
        passes.append((ROBOT_DIR / "robot_antenna.png", R["w"], R["x"], y_expr,
                       f"if({talk},if({flicker},if({blink},0,1),0),0)"))
        passes.append((ROBOT_DIR / "robot_blink.png", R["w"], R["x"], y_expr,
                       f"if({talk},if({blink},1,0),0)"))

    for i, (png, w, x, y_expr, enable) in enumerate(passes):
        nxt = workdir / f"tmp_stk{i}.mp4"
        last = (i == len(passes) - 1)
        overlay_pass(cur, nxt, png, w, x, y_expr, enable, last)
        cur = nxt
        print(f"[render] pass {i + 1}/{len(passes)}: {Path(png).stem} ok")

    if not passes:  # nothing to overlay: mux voice directly
        cmd = ["ffmpeg", "-y", "-nostdin", "-i", str(tmp), "-i", str(voice),
               "-map", "0:v", "-map", "1:a", "-c:v", "copy",
               "-c:a", "aac", "-b:a", "128k", "-shortest",
               "-movflags", "+faststart", str(out_path)]
        _run(cmd)
    else:
        shutil.move(str(cur), str(out_path))
    tmp.unlink(missing_ok=True)
    print(f"[render] {out_path.name} done ({total:.1f}s, "
          f"{len(sticker_sids)} stickers + robot:{has_robot})")


if __name__ == "__main__":
    render(Path(sys.argv[1]), Path(sys.argv[2]))
