"""Rebuild the bg pool from Pixabay — HD, story-matched categories
(boss round-8: 'use laborers working / matching vibes, not random space
footage, and NO low-res'). Runs on GH runners where PIXABAY_API_KEY lives.

Downloads the most popular >=1080p clip per category, applies the boss-law
transform (mute + mirror + 1.09 zoom + grade + speed), cuts 118s, then the
workflow swaps the release assets.
"""
import json, os, subprocess, sys, urllib.request, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

CATS = {  # story-matched pool, never random
    "working":     ["construction workers", "worker", "laborer"],
    "school":      ["classroom", "students", "school"],
    "food":        ["cooking", "street food", "kitchen"],
    "city":        ["city street night", "traffic", "busy street"],
    "satisfying":  ["satisfying", "slime", "paint"],
}


def best_url(query):
    key = os.environ["PIXABAY_API_KEY"]
    url = ("https://pixabay.com/api/videos/?key=" + key + "&q="
           + urllib.request.quote(query)
           + "&video_type=film&per_page=40&safesearch=true")
    req = urllib.request.Request(url)  # honest UA (no fake browser prints)
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    hits = [h for h in data.get("hits", []) if h.get("videos")]
    hits.sort(key=lambda h: -(h.get("downloads") or 0))
    for h in hits[:10]:
        v = h["videos"]
        f = next((v[k] for k in ("large", "medium")
                  if k in v and v[k].get("height", 0) >= 1080), None)
        if f and (h.get("duration") or 0) >= 5:  # short is fine — we loop
            return f["url"], h.get("duration")
    return None, 0


def main():
    out = Path("pool_out"); out.mkdir(exist_ok=True)
    w, h, fps = config.SHORT["w"], config.SHORT["h"], config.SHORT["fps"]
    for cat, queries in CATS.items():
        dst = out / f"pool_{cat}.mp4"
        got = None
        for q in queries:
            print(f"[pool] {cat}: searching '{q}'…")
            try:
                u, dur = best_url(q)
            except Exception as e:
                print(f"  search failed: {e}"); continue
            if not u:
                continue
            r = subprocess.run(["ffmpeg", "-y", "-nostdin", "-stream_loop", "-1",
                                "-i", u,
                "-vf", (f"hflip,scale={int(w*1.09)}:{int(h*1.09)}:"
                        "force_original_aspect_ratio=increase,"
                        f"crop={w}:{h},eq=saturation=1.09:contrast=1.05,"
                        f"hue=h=7,fps={fps},setpts=1.05*PTS"),
                "-t", "118", "-an", "-c:v", "libx264",
                "-preset", config.X264["preset"], "-crf", config.X264["crf"],
                str(dst)], capture_output=True)
            if r.returncode == 0 and dst.exists():
                print(f"  -> pool_{cat}.mp4 OK ({dst.stat().st_size/1e6:.0f}MB)")
                got = dst
                break
        if not got:
            print(f"  !! no usable clip for {cat}")
    print("[pool] done:", sorted(f.name for f in out.glob('*.mp4')))


if __name__ == "__main__":
    main()
