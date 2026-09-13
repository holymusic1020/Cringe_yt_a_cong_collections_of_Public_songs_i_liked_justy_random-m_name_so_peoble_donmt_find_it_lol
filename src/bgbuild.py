"""BG v2 — MULTI-CLIP backgrounds (boss round-12: 'you are just repeating
one scene in the background'). Every episode's bg is a sequence of 3
segments cut from DIFFERENT pool clips at random offsets with different hue
shifts — no visible repetition, always story-matched when hints exist.
"""
import random, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

KEYWORDS = {
    "school": ("classroom", "student", "school", "exam", "chalk", "lesson"),
    "food": ("food", "cooking", "kitchen", "samosa", "canteen", "street food"),
    "working": ("worker", "labor", "construction", "working", "job", "build"),
    "city": ("city", "street", "traffic", "urban", "night", "scooter"),
    "satisfying": ("satisfying", "slime", "paint", "craft", "soap", "sand"),
}


def _probe_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _segment(src, dur, hue, dst, w, h, fps):
    d = _probe_dur(src)
    cmd = ["ffmpeg", "-y", "-nostdin"]
    if d >= dur + 2:
        off = random.uniform(0, d - dur - 1)
        cmd += ["-ss", f"{off:.2f}", "-i", str(src)]
    else:
        cmd += ["-stream_loop", "-1", "-i", str(src)]
    cmd += ["-vf", (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"crop={w}:{h},hue=h={hue},fps={fps}"),
            "-t", f"{dur:.2f}", "-an", "-c:v", "libx264",
            "-preset", config.X264["preset"], "-crf", config.X264["crf"],
            "-threads", "2", str(dst)]
    subprocess.run(cmd, capture_output=True, check=True)


def build_bg(hints, duration, workdir):
    """3 segments from 3 different clips -> concat. Returns bg.mp4 path."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    pool = sorted((config.ASSETS / "bg_pool").glob("*.mp4"))
    if not pool:
        raise RuntimeError("bg pool empty — run pool_refresh first")
    want = set()
    for h in (hints or []):
        hl = h.lower()
        for cat, kws in KEYWORDS.items():
            if any(k in hl for k in kws):
                want.add(cat)
    matches = [p for p in pool if any(w in p.stem for w in want)] if want else []
    # 3 DIFFERENT clips: prefer matches, fill from the rest — never repeat
    picks = matches[:]
    random.shuffle(picks)
    for p in pool:
        if len(picks) >= 3:
            break
        if p not in picks:
            picks.append(p)
    picks = picks[:3]
    w, h, fps = config.SHORT["w"], config.SHORT["h"], config.SHORT["fps"]
    segs, durs = [], []
    weights = [0.42, 0.33, 0.25]
    for i, clip in enumerate(picks):
        seg_d = duration * weights[i] if i < len(picks) - 1 else \
            duration - sum(durs)
        seg = workdir / f"bgseg_{i}.mp4"
        _segment(clip, seg_d + 0.3, random.choice([-14, -9, -5, 5, 9, 14]),
                 seg, w, h, fps)
        segs.append(seg)
        durs.append(seg_d)
    lst = workdir / "bglist.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    dst = workdir / "bg.mp4"
    # RE-ENCODE the concat (NOT -c copy): pool clips carry different
    # colorspace tags, and the mid-stream parameter change at a segment
    # boundary deadlocks overlay-heavy filtergraphs (stall at 44.2s, runs
    # g/h). One uniform encode = single continuous stream, no reconfigure.
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-f", "concat", "-safe", "0",
                    "-i", str(lst),
                    "-vf", "format=yuv420p,setsar=1",
                    "-c:v", "libx264", "-preset", config.X264["preset"],
                    "-crf", "18", "-threads", "2",
                    "-colorspace", "bt709", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-color_range", "tv",
                    "-an", str(dst)],
                   capture_output=True, check=True)
    for s in segs:
        s.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    print(f"[bg] multi-clip: {len(picks)} different clips "
          f"({', '.join(p.stem for p in picks)}), no repeats")
    return dst
