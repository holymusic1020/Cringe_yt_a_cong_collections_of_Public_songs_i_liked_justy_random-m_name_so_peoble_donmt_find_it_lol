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


def best_urls(query, n=2):
    """Top-n HD clip urls for a query (variety: pool gets 2 per category)."""
    key = os.environ["PIXABAY_API_KEY"]
    url = ("https://pixabay.com/api/videos/?key=" + key + "&q="
           + urllib.request.quote(query)
           + "&video_type=film&per_page=40&safesearch=true")
    req = urllib.request.Request(url)  # honest UA (no fake browser prints)
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    hits = [h for h in data.get("hits", []) if h.get("videos")]
    hits.sort(key=lambda h: -(h.get("downloads") or 0))
    out = []
    for h in hits[:12]:
        v = h["videos"]
        f = next((v[k] for k in ("large", "medium")
                  if k in v and v[k].get("height", 0) >= 1080), None)
        if f and (h.get("duration") or 0) >= 5 and f["url"] not in out:
            out.append(f["url"])
        if len(out) >= n:
            break
    return out


def pexels_urls(query, n=2):
    """Pexels fallback when Pixabay yields nothing (quota/key trouble)."""
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        print("  pexels: NO KEY in env (workflow must pass PEXELS_API_KEY)")
        return []
    url = ("https://api.pexels.com/videos/search?query="
           + urllib.parse.quote(query) + "&per_page=30")
    req = urllib.request.Request(url, headers={"Authorization": key})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    vids = [v for v in data.get("videos", []) if (v.get("duration") or 0) >= 5]
    print(f"  pexels '{query}': {len(vids)} usable of {len(data.get('videos', []))} results")
    out = []
    for v in vids:
        files = [f for f in v.get("video_files", [])
                 if f.get("height", 0) >= 1080
                 and (f.get("file_type") or "video/mp4") == "video/mp4"]
        if files:
            f = sorted(files, key=lambda f: f["height"])[0]  # smallest >=1080
            if f["link"] not in out:
                out.append(f["link"])
        if len(out) >= n:
            break
    return out


def main():
    out = Path("pool_out"); out.mkdir(exist_ok=True)
    w, h, fps = config.SHORT["w"], config.SHORT["h"], config.SHORT["fps"]
    for cat, queries in CATS.items():
        got = None
        for q in queries:
            print(f"[pool] {cat}: searching '{q}'…")
            try:
                urls = best_urls(q, n=2)
            except Exception as e:
                print(f"  pixabay failed ({e}) — trying pexels")
                try:
                    urls = pexels_urls(q, n=2)
                except Exception as e2:
                    print(f"  pexels failed too: {e2}"); continue
            for ui, u in enumerate(urls):
                dst = out / f"pool_{cat}_{ui + 1}.mp4"
                r = subprocess.run(["ffmpeg", "-y", "-nostdin", "-stream_loop", "-1",
                                    "-i", u,
                "-vf", (f"hflip,scale={int(w*1.09)}:{int(h*1.09)}:"
                        "force_original_aspect_ratio=increase,"
                        f"crop={w}:{h},eq=saturation=1.09:contrast=1.05,"
                        f"hue=h=7,fps={fps},setpts=1.05*PTS"),
                    "-t", "118", "-an", "-c:v", "libx264",
                    "-preset", config.X264["preset"], "-crf", config.X264["crf"],
                    str(dst)], capture_output=True)
                if r.returncode == 0 and dst.exists() and dst.stat().st_size > 1e6:
                    print(f"  -> {dst.name} OK ({dst.stat().st_size/1e6:.0f}MB)")
                    got = dst
                else:
                    print(f"  !! ffmpeg failed for {u[:70]} rc={r.returncode}")
                    if r.stderr:
                        print("   ", r.stderr.decode(errors="replace")[-200:].strip())
            if got:
                break
        if not got:
            print(f"  !! no usable clip for {cat}")
    built = sorted(f.name for f in out.glob('*.mp4'))
    print("[pool] done:", built)
    if len(built) < 3:
        # exit 0 with an empty pool = the Sep 27 wipe (workflow deleted the
        # good assets because 'nothing was built' looked like success)
        print("[pool] FATAL: fewer than 3 categories built — refusing "
              "to let the swap touch the existing pool", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
