"""Final compose: bg video + per-speaker sticker pop-ins + karaoke ass + voice.

Stickers get name-tags baked in with PIL (no drawtext escaping hell).
Layout (1080x1920): sticker bottom-left, captions above it, bg everywhere.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _run(cmd, timeout=1500):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({p.returncode}): {p.stderr[-1200:]}")
    return p


def _drop_caches():
    """Best-effort: reclaim page cache so encoder passes have headroom."""
    for c in (["sudo", "-n", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
              ["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"]):
        try:
            if subprocess.run(c, capture_output=True, timeout=15).returncode == 0:
                print("[render] page cache dropped"); return
        except Exception:
            pass


def _run_resilient(cmd, timeout=1500, tries=3, cool=15):
    """Retry on SIGKILL (-9): transient sandbox memory pressure, not our bug."""
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
    name = char["name"].split(" (")[0]  # "Lubna (Mom)" -> "Lubna"
    font = ImageFont.truetype(FONT_BOLD, 46)
    tw = bd.textlength(name, font=font)
    bd.text(((im.width - tw) / 2, 18), name, font=font, fill=(255, 255, 255, 255))
    canvas.paste(bar, (0, im.height), bar)
    canvas.save(out_path)
    return out_path


def render(workdir, out_path):
    workdir = Path(workdir)
    tl = json.loads((workdir / "timeline.json").read_text())
    total = tl["total_s"]
    bg, voice, caps = workdir / "bg.mp4", workdir / "voice.mp3", workdir / "captions.ass"

    windows = {}
    for line in tl["lines"]:
        windows.setdefault(line["speaker"], []).append((line["start"], line["end"]))

    sticker_sids = [s for s in windows if s in config.HAS_STICKER][:4]

    def sticker_pos(tagged_png):
        """Bottom-anchor: small deliberate gap above frame edge (boss request)."""
        w0, h0 = Image.open(tagged_png).size
        h_scaled = int(h0 * config.LAYOUT["sticker_w"] / w0)
        return (config.LAYOUT["sticker_x"],
                config.SHORT["h"] - config.LAYOUT["sticker_bottom_gap"] - h_scaled)

    # ── TWO-PASS render (2GB-runner friendly): captions first, stickers second
    # Pass A: bg + karaoke captions -> tmp
    tmp = workdir / "tmp_capped.mp4"
    _run_resilient(["ffmpeg", "-y", "-nostdin", "-i", str(bg),
          "-vf", f"ass=filename='{caps}':fontsdir='/usr/share/fonts/truetype/dejavu',format=yuv420p",
          "-t", f"{total:.2f}", "-r", str(config.SHORT["fps"]),
          "-c:v", "libx264", "-preset", config.X264["preset"],
          "-crf", config.X264["crf"], "-an", str(tmp)])
    # free memory + cache: bg and per-line mp3s are spent after pass A
    bg.unlink(missing_ok=True)
    for f in workdir.glob("line_*.mp3"):
        f.unlink(missing_ok=True)
    for f in workdir.glob("bg_raw*"):
        f.unlink(missing_ok=True)
    _drop_caches()

    # Pass B: one sticker per pass (light graph — 2GB runners can't take 5 inputs)
    cur = tmp
    for i, sid in enumerate(sticker_sids):
        tagged = bake_nametag(sid, workdir / f"tagged_{sid}.png")
        sx, sy = sticker_pos(tagged)
        enable = "+".join(f"between(t,{s:.2f},{e:.2f})" for s, e in windows[sid])
        nxt = workdir / f"tmp_stk{i}.mp4"
        last = (i == len(sticker_sids) - 1)
        cmd = ["ffmpeg", "-y", "-nostdin",
               "-i", str(cur),
               "-loop", "1", "-r", str(config.SHORT["fps"]),
               "-t", f"{total:.2f}", "-i", str(tagged)]
        if last:
            cmd += ["-i", str(voice)]
        cmd += ["-filter_complex",
                f"[1:v]scale={config.LAYOUT['sticker_w']}:-2,format=rgba[stk];"
                f"[0:v][stk]overlay=x={sx}:y={sy}:"
                f"enable='{enable}':eval=init,format=yuv420p[vout]",
                "-map", "[vout]"]
        if last:
            cmd += ["-map", "2:a", "-c:a", "aac", "-ar", "44100",
                    "-b:a", "128k", "-shortest"]
        cmd += ["-t", f"{total:.2f}", "-r", str(config.SHORT["fps"]),
                "-c:v", "libx264", "-preset", config.X264["preset"],
                "-crf", "16" if not last else config.X264["crf"]]
        cmd.append(str(nxt))
        _run_resilient(cmd)
        if cur != tmp:
            cur.unlink(missing_ok=True)
        cur = nxt
    if not sticker_sids:  # no stickers: mux voice onto capped bg
        cmd = ["ffmpeg", "-y", "-nostdin", "-i", str(tmp), "-i", str(voice),
               "-map", "0:v", "-map", "1:a", "-c", "copy",
               "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_path)]
        _run(cmd)
    else:
        shutil.move(str(cur), str(out_path))
    tmp.unlink(missing_ok=True)
    print(f"[render] {out_path.name} done ({total:.1f}s, {len(sticker_sids)} stickers)")


if __name__ == "__main__":
    render(Path(sys.argv[1]), Path(sys.argv[2]))
