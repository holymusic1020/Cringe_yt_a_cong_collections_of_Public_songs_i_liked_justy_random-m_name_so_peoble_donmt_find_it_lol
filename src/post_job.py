"""The cadence brain: posts ONE episode to YouTube per run.

Boss law: 1 Short every 15-19 HOURS (randomized, human-like).
Source: render.yml artifacts (the vault). FIFO: oldest unposted artifact first.

Modes:
  python src/post_job.py --episode ep001 [--force]   # manual dispatch
  python src/post_job.py                             # scheduled: respects window

Flow: pick ep -> preflight binding -> upload UNLISTED -> verify live ->
flip PUBLIC (constitution: unlisted-first, verify, then publish) ->
commit state/state.json (dup-title guard) -> Telegram receipt.
"""
import argparse, json, os, random, subprocess, sys, time, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config, tg
from yt import YT

STATE = config.ROOT / "state" / "state.json"
CADENCE_H = (15, 19)  # boss spec


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"posted": [], "next_post_at": None, "last_artifact_id": 0}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1))


def gh_api(path):
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    r = requests.get(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{path}",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_artifact(art, dest):
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    r = requests.get(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/artifacts/{art['id']}/zip",
        headers={"Authorization": f"Bearer {tok}"}, timeout=120)
    r.raise_for_status()
    z = dest / f"art_{art['id']}.zip"
    z.write_bytes(r.content)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(dest / f"art_{art['id']}")
    return dest / f"art_{art['id']}"


def pick_episode(st, want=None):
    """Returns (mp4, meta) — FIFO unposted artifact, or the requested stem."""
    dest = Path("/tmp/postwork"); dest.mkdir(parents=True, exist_ok=True)
    arts = gh_api("actions/artifacts?per_page=30")["artifacts"]
    arts = [a for a in arts if not a["expired"] and a["id"] > (st.get("last_artifact_id") or 0)]
    arts.sort(key=lambda a: a["id"])  # FIFO
    for a in arts:
        d = fetch_artifact(a, dest)
        mp4s = sorted(d.glob("*.mp4"))
        if not mp4s:
            continue
        for mp4 in mp4s:
            stem = mp4.stem
            if want and stem != want:
                continue
            if any(p["stem"] == stem for p in st["posted"]):
                continue  # already posted
            meta_p = d / f"{stem}_meta.json"
            meta = json.loads(meta_p.read_text()) if meta_p.exists() else {
                "title": stem, "description": "", "tags": [],
                "category_id": config.YT_CATEGORY_ID}
            st["_artifact_id"] = a["id"]
            return mp4, meta
    return None, None


def dup_title_fix(title, st):
    titles = {p["title"] for p in st["posted"]}
    if title not in titles:
        return title
    for suf in config.DUPE_SUFFIXES:
        if title + suf not in titles:
            return title + suf
    return f"{title} ({int(time.time())})"


def commit_state(st):
    if os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
        subprocess.run(["git", "config", "user.name", "nixfav-engine"], check=True)
        subprocess.run(["git", "config", "user.email",
                        "engine@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "state/state.json"], check=True)
        subprocess.run(["git", "commit", "-m",
                        f"state: posted {st['posted'][-1]['stem']} "
                        f"({st['posted'][-1]['video_id']})"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("[post] state committed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    st = load_state()
    now = datetime.now(timezone.utc)

    if not args.force and not args.episode and st.get("next_post_at"):
        nxt = datetime.fromisoformat(st["next_post_at"])
        if now < nxt:
            wait_h = (nxt - now).total_seconds() / 3600
            print(f"[post] cadence window: next post in {wait_h:.1f}h — sleeping")
            return

    mp4, meta = pick_episode(st, args.episode)
    if not mp4:
        print("[post] nothing unposted in the vault")
        return

    print(f"[post] episode: {mp4.stem} | {meta['title']}")
    yt = YT()
    ch = yt.whoami()
    print(f"[post] channel binding verified: {ch['title']}")
    meta["title"] = dup_title_fix(meta["title"], st)
    meta["privacy"] = "unlisted"  # constitution: unlisted first
    vid = yt.upload(mp4, meta)

    live = yt.verify(vid)
    print(f"[post] live verify: {live['title']} | {live['duration']} | "
          f"{live['privacy']} @ {live['channel']}")
    assert live["channel"] == ch["title"], "channel mismatch?!"

    yt.set_privacy(vid, "public")
    live2 = yt.verify(vid)
    url = f"https://youtu.be/{vid}"
    print(f"[post] PUBLIC ✅ {url} ({live2['privacy']})")

    st["posted"].append({"stem": mp4.stem, "video_id": vid,
                         "title": meta["title"],
                         "at": now.isoformat()})
    st["last_artifact_id"] = max(st.get("last_artifact_id") or 0,
                                 st.pop("_artifact_id", 0))
    st["next_post_at"] = (now + timedelta(
        hours=random.uniform(*CADENCE_H))).isoformat()
    save_state(st)
    commit_state(st)
    tg.send_message(f"🚀 POSTED to {ch['title']}: {meta['title']}\n{url}")


if __name__ == "__main__":
    main()
