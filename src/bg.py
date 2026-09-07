"""Background provider chain: REAL VIDEO first (boss law), generated = plan C.

pexels_video        → Pexels API (free key) — satisfying/ASMR b-roll, direct DL
nocopyright_gameplay→ yt-dlp free-use gameplay channels (playbook §4 throttling)
generated_image     → LAST resort: assets/bg PNG + Ken Burns zoompan

Every episode gets a different bg + different random segment = anti-template.
"""
import os, random, subprocess, sys, json, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def log(msg):
    print(f"[bg] {msg}", flush=True)


def _run(cmd, timeout=240):
    """ffmpeg/yt-dlp runner — always surface stderr (playbook §5)."""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}): {p.stderr[-800:]}")
    return p


def _probe_duration(path):
    p = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "json", str(path)])
    return float(json.loads(p.stdout)["format"]["duration"])


def _cut_cover(src, duration, dst):
    """Random segment, cover-scale to 1080x1920@30, silent (audio comes later)."""
    total = _probe_duration(src)
    start = random.uniform(0, max(0, total - duration - 5))
    _run([
        "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(src),
        "-t", f"{duration:.2f}",
        "-vf", (f"scale={config.SHORT['w']}:{config.SHORT['h']}:"
                "force_original_aspect_ratio=increase,"
                f"crop={config.SHORT['w']}:{config.SHORT['h']},"
                f"fps={config.SHORT['fps']}"),
        "-an", "-c:v", "libx264", "-preset", config.X264["preset"],
        "-crf", config.X264["crf"], str(dst),
    ])
    log(f"cut {duration:.0f}s @ {start:.0f}s offset -> {dst.name}")


def _bg_pexels_video(energy, duration, workdir, used_names):
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no PEXELS_API_KEY")
    kind = config.PEXELS_QUERIES.get(
        config.BG_ENERGY_MAP.get(energy, "satisfying"), "satisfying")
    query = random.choice(config.PEXELS_QUERIES[kind])
    url = ("https://api.pexels.com/videos/search?query="
           + urllib.request.quote(query) + "&per_page=25&orientation=portrait")
    req = urllib.request.Request(url, headers={"Authorization": key})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    vids = [v for v in data.get("videos", [])
            if v.get("video_files") and v["user"]["name"] not in used_names]
    if not vids:
        raise RuntimeError("pexels: no results")
    v = random.choice(vids)
    files = [f for f in v["video_files"]
             if f.get("height", 0) >= 1080 and f.get("file_type") == "video/mp4"]
    if not files:
        files = [f for f in v["video_files"] if f.get("file_type") == "video/mp4"]
    best = sorted(files, key=lambda f: f.get("height", 0))[0]
    raw = workdir / "bg_raw.mp4"
    urllib.request.urlretrieve(best["link"], raw)
    used_names.add(v["user"]["name"])
    log(f"pexels: '{query}' by {v['user']['name']} ({best.get('width')}x{best.get('height')})")
    return raw, f"Background footage: {v['user']['name']} via Pexels"


def _bg_nocopyright_gameplay(energy, duration, workdir, used_names):
    src = random.choice(config.NOCOPYRIGHT_SOURCES)
    raw = workdir / "bg_raw.mp4"
    # list-then-download (playbook §4): probe duration first, pick a valid window
    info = _run([
        "yt-dlp", "-J", "--no-playlist",
        f"https://www.youtube.com/watch?v={src['video_id']}",
    ], timeout=120)
    total = float(json.loads(info.stdout).get("duration") or 0)
    if total < duration + 90:
        raise RuntimeError(f"source too short ({total:.0f}s)")
    start = random.uniform(30, total - duration - 60)
    end = start + duration + 15
    _run([
        "yt-dlp",
        "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]",
        "--merge-output-format", "mp4",
        "--download-sections", f"*{start:.0f}-{end:.0f}",
        "--sleep-requests", "3", "--sleep-interval", "6", "--retries", "4",
        "-o", str(raw),
        f"https://www.youtube.com/watch?v={src['video_id']}",
    ], timeout=400)
    log(f"gameplay: {src['credit']} ({src['kind']})")
    return raw, config.BG_CREDIT["nocopyright_gameplay"].format(credit=src["credit"])


def _bg_generated_image(energy, duration, workdir, used_names):
    plates = sorted((config.ASSETS / "bg").glob("*.png"))
    if not plates:
        raise RuntimeError("no generated bg plates")
    plate = random.choice(plates)
    dst = workdir / "bg.mp4"
    z = random.choice([("zoom-in", "min(zoom+0.0006,1.20)"),
                       ("zoom-out", "max(1.20-0.0006*on,1.0)")])
    frames = int(duration * config.SHORT["fps"])
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(plate),
        "-vf", (f"scale={config.SHORT['w']}:{config.SHORT['h']}:"
                "force_original_aspect_ratio=increase,"
                f"crop={config.SHORT['w']}:{config.SHORT['h']},"
                f"zoompan=z='{z[1]}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s={config.SHORT['w']}x{config.SHORT['h']}:"
                f"fps={config.SHORT['fps']}"),
        "-t", f"{duration:.2f}", "-an",
        "-c:v", "libx264", "-preset", config.X264["preset"],
        "-crf", config.X264["crf"], str(dst),
    ])
    log(f"generated (plan C): {plate.name} {z[0]} — real video preferred next run")
    return dst, None


def fetch_bg(energy, duration, workdir):
    """Returns (bg_video_path, credit_line_or_None). Tries providers in order."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    used = set()
    for provider in config.BG_PRIORITY:
        try:
            if provider == "generated_image":
                return _bg_generated_image(energy, duration, workdir, used)
            raw, credit = (globals()[f"_bg_{provider}"](energy, duration, workdir, used))
            dst = workdir / "bg.mp4"
            _cut_cover(raw, duration, dst)
            raw.unlink(missing_ok=True)
            return dst, credit
        except Exception as e:
            log(f"provider {provider} failed: {e}")
    raise RuntimeError("all background providers failed")


if __name__ == "__main__":
    # local test: python src/bg.py <energy> <duration>
    energy = sys.argv[1] if len(sys.argv) > 1 else "chill"
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 40
    path, credit = fetch_bg(energy, dur, Path("/tmp/bgtest"))
    print(f"OK {path} | {credit} | {_probe_duration(path):.1f}s")
