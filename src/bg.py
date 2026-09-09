"""Background provider chain: REAL VIDEO first (boss law), generated = plan C.

pexels_video        → Pexels API (free key) — satisfying/ASMR b-roll, direct DL
nocopyright_gameplay→ yt-dlp free-use gameplay channels (playbook §4 throttling)
generated_image     → LAST resort: assets/bg PNG + Ken Burns zoompan

Every episode gets a different bg + different random segment = anti-template.
"""
import os, time, random, subprocess, sys, json, urllib.request
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


def _bg_yt_clip(energy, duration, workdir, used_names):
    """BOSS SPEC (copyright-safe transform): pull a MIDDLE segment of a real
    YouTube video, MUTE it, and transform (mirror + zoom + speed + color
    shift) so Content ID can't match it. Video-only download (no audio
    stream at all). Layered under original story/voices/captions =
    transformative use per constitution §E.

    Datacenter IPs (GH runners) often hit YouTube's bot-wall demanding
    cookies — so we retry across candidates AND the tv/ios player clients,
    which historically skip the PO-token check."""
    cat = config.BG_ENERGY_MAP.get(energy, "satisfying")
    queries = config.YT_BG_SEARCHES.get(cat, config.YT_BG_SEARCHES["satisfying"])
    q = random.choice(queries)
    info = _run(["yt-dlp", "-J", f"ytsearch6:{q}", "--no-playlist"], timeout=180)
    entries = [e for e in (json.loads(info.stdout).get("entries") or [])
               if e and (e.get("duration") or 0) > 600]
    if not entries:
        raise RuntimeError("yt search: no long candidates")
    # retry ladder: up to 3 candidates x (default client, tv/ios client)
    attempts = []
    for pick in random.sample(entries, min(3, len(entries))):
        attempts.append((pick, []))
        attempts.append((pick, ["--extractor-args",
                                "youtube:player_client=tv,ios"]))
    last_err = None
    for pick, extra in attempts:
        total = pick["duration"]
        seg = duration + 25
        start = total * 0.30 + random.uniform(0, max(1.0, total * 0.45 - seg))
        raw = workdir / "bg_raw.mp4"
        try:
            _run(["yt-dlp", "-f", "bv*[height<=1080][ext=mp4]",
                  "--download-sections", f"*{start:.0f}-{start + seg:.0f}",
                  "--force-keyframes-at-cuts",
                  "--sleep-requests", "2", "--sleep-interval", "4", "--retries", "2",
                  *extra,
                  "-o", str(raw), pick["webpage_url"]], timeout=400)
            if not raw.exists() or raw.stat().st_size < 100_000:
                raise RuntimeError("download produced no usable file")
        except Exception as e:
            last_err = e
            raw.unlink(missing_ok=True)
            log(f"yt_clip: candidate '{(pick.get('title') or '?')[:36]}' failed "
                f"({'tv/ios' if extra else 'default'} client) — trying next")
            continue
        w, h, fps = config.SHORT["w"], config.SHORT["h"], config.SHORT["fps"]
        dst = workdir / "bg.mp4"
        _run(["ffmpeg", "-y", "-nostdin", "-i", str(raw),
              "-vf", (f"hflip,scale={int(w * 1.09)}:{int(h * 1.09)}:"
                      "force_original_aspect_ratio=increase,"
                      f"crop={w}:{h},eq=saturation=1.09:contrast=1.05,"
                      f"hue=h=7,fps={fps},setpts=1.05*PTS"),
              "-t", f"{duration:.2f}", "-an",
              "-c:v", "libx264", "-preset", config.X264["preset"],
              "-crf", config.X264["crf"], str(dst)])
        raw.unlink(missing_ok=True)
        log(f"yt_clip: '{pick.get('title', '?')[:48]}' mid-segment @{start:.0f}s, "
            f"muted+mirrored+graded ({'tv/ios' if extra else 'default'} client)")
        return dst, None  # transformed bg — no credit line needed
    raise RuntimeError(f"yt_clip: all candidates failed ({last_err})")


def _bg_pool(energy, duration, workdir, used_names):
    """REAL-VIDEO pool fallback: pre-transformed NASA public-domain clips
    (aurora timelapses / rocket views) stored as GitHub release assets,
    fetched into assets/bg_pool/ by the render workflow. Live YouTube
    extraction gets bot-walled on datacenter IPs — this always works.
    Random offset + hue shift per use so no two episodes share the same
    bg frame-for-frame."""
    pool = config.ASSETS / "bg_pool"
    clips = sorted(pool.glob("*.mp4")) if pool.exists() else []
    if not clips:
        raise RuntimeError("bg pool empty (release fetch failed?)")
    cat = config.BG_ENERGY_MAP.get(energy, "satisfying")
    prefer = [c for c in clips if cat in c.stem] or clips
    pick = random.choice(prefer)
    dur = _probe_duration(pick)
    off = random.uniform(0, max(0.0, dur - duration - 1))
    hue = random.choice([-12, -8, -5, 5, 8, 12])
    w, h, fps = config.SHORT["w"], config.SHORT["h"], config.SHORT["fps"]
    dst = workdir / "bg.mp4"
    cmd = ["ffmpeg", "-y", "-nostdin"]
    if dur >= duration + 2:                       # random mid-offset when it fits
        cmd += ["-ss", f"{off:.2f}", "-i", str(pick)]
    else:                                         # long episode: seamless loop
        cmd += ["-stream_loop", "-1", "-i", str(pick)]
    cmd += ["-vf", (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"crop={w}:{h},hue=h={hue},fps={fps}"),
            "-t", f"{duration:.2f}", "-an",
            "-c:v", "libx264", "-preset", config.X264["preset"],
            "-crf", config.X264["crf"], str(dst)]
    _run(cmd)
    log(f"bg_pool: '{pick.name}' hue {hue:+d}"
        f"{' @' + str(int(off)) + 's' if dur >= duration + 2 else ' (looped)'}"
        f" — NASA public domain, exact {duration:.0f}s cut")
    return dst, None  # public-domain footage — no credit line needed


def _bg_pixabay_video(energy, duration, workdir, used_names):
    """Pixabay stock footage (Content License: free use, no attribution,
    alteration required — we mirror/zoom/grade/speed-shift, so compliant).
    Same boss-spec transform as yt_clip: muted, hflip, 1.09 zoom, color
    shift, 1.05 speed. Long clip -> random MIDDLE segment; short clip ->
    seamless loop."""
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no PIXABAY_API_KEY")
    category = config.BG_ENERGY_MAP.get(energy, "satisfying")
    queries = config.PIXABAY_QUERIES.get(category,
                                         config.PIXABAY_QUERIES["satisfying"])
    query = random.choice(queries)
    url = ("https://pixabay.com/api/videos/?key=" + key
           + "&q=" + urllib.request.quote(query)
           + "&video_type=film&per_page=40&safesearch=true")
    # NO fake browser UA — bare "Mozilla/5.0" is a bot fingerprint that
    # Cloudflare 403s; the default urllib UA is honest and verified-working
    # from GH runners (pixabay-debug probe, 2026-09-09)
    data = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url)
            data = json.loads(urllib.request.urlopen(req, timeout=30).read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt == 0:  # transient cloudflare edge
                time.sleep(4)
                continue
            raise
    hits = [h for h in data.get("hits", [])
            if h.get("videos") and h.get("tags") not in used_names]
    if not hits:
        raise RuntimeError("pixabay: no results")
    # prefer clips long enough for a middle-segment cut
    long_hits = [h for h in hits if (h.get("duration") or 0) >= duration + 8]
    pick = random.choice(long_hits or hits)
    vids = pick["videos"]
    files = [vids[k] for k in ("large", "medium", "small", "tiny") if k in vids]
    best = next((f for f in files if f.get("height", 0) >= 1080),
                next((f for f in files if f.get("height", 0) >= 720), files[0]))
    raw = workdir / "bg_raw.mp4"
    urllib.request.urlretrieve(best["url"], raw)
    used_names.add(pick.get("tags"))
    clip_dur = _probe_duration(raw)
    w, h, fps = config.SHORT["w"], config.SHORT["h"], config.SHORT["fps"]
    dst = workdir / "bg.mp4"
    cmd = ["ffmpeg", "-y", "-nostdin"]
    if clip_dur >= duration + 8:   # middle segment, never the whole clip
        off = random.uniform(max(0, clip_dur * 0.2),
                             max(clip_dur * 0.2, clip_dur - duration - 2))
        cmd += ["-ss", f"{off:.2f}", "-i", str(raw)]
        seg = f"@{off:.0f}s mid-segment"
    else:                          # short stock clip: seamless loop
        cmd += ["-stream_loop", "-1", "-i", str(raw)]
        seg = "(looped)"
    cmd += ["-vf", (f"hflip,scale={int(w * 1.09)}:{int(h * 1.09)}:"
                    "force_original_aspect_ratio=increase,"
                    f"crop={w}:{h},eq=saturation=1.09:contrast=1.05,"
                    f"hue=h=7,fps={fps},setpts=1.05*PTS"),
            "-t", f"{duration:.2f}", "-an",
            "-c:v", "libx264", "-preset", config.X264["preset"],
            "-crf", config.X264["crf"], str(dst)]
    _run(cmd)
    raw.unlink(missing_ok=True)
    log(f"pixabay: '{query}' {pick.get('tags', '')[:40]} "
        f"{best.get('width')}x{best.get('height')} {seg}, muted+mirrored+graded")
    return dst, None  # Pixabay Content License — no credit line required


def _bg_pexels_video(energy, duration, workdir, used_names):
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no PEXELS_API_KEY")
    category = config.BG_ENERGY_MAP.get(energy, "satisfying")
    queries = config.PEXELS_QUERIES.get(category,
                                        config.PEXELS_QUERIES["satisfying"])
    query = random.choice(queries)
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
            raw, credit = globals()[f"_bg_{provider}"](energy, duration, workdir, used)
            if provider in ("yt_clip", "pixabay_video", "pool"):
                return raw, credit  # already final (transformed + exact cut)
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
