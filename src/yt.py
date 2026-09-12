"""YouTube Data API v3 via plain REST (requests only — no google libs needed).

Playbook §7 laws: .strip() every secret, unlisted-first, verify live or broken.
"""
import os, time
import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _env(name):
    return os.environ.get(name, "").strip()


class YT:
    def __init__(self):
        self.client_id = _env("YOUTUBE_CLIENT_ID")
        self.client_secret = _env("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = _env("YOUTUBE_REFRESH_TOKEN")
        if not all((self.client_id, self.client_secret, self.refresh_token)):
            raise RuntimeError("missing YT secrets (CLIENT_ID/SECRET/REFRESH_TOKEN)")
        self._tok = None
        self._tok_exp = 0

    @property
    def token(self):
        if self._tok and time.time() < self._tok_exp - 60:
            return self._tok
        r = requests.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }, timeout=30)
        r.raise_for_status()
        d = r.json()
        if "access_token" not in d:
            raise RuntimeError(f"token refresh failed: {d}")
        self._tok = d["access_token"]
        self._tok_exp = time.time() + int(d.get("expires_in", 3600))
        print(f"[yt] access token refreshed (expires in {d.get('expires_in')}s)")
        return self._tok

    def whoami(self):
        """PROOF of channel binding — constitution: verify before every battle."""
        r = requests.get(f"{API}/channels", params={
            "part": "snippet,statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {self.token}"}, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            raise RuntimeError("no channel bound to this token!")
        ch = items[0]
        return {"title": ch["snippet"]["title"],
                "id": ch["id"],
                "subs": ch["statistics"].get("subscriberCount"),
                "videos": ch["statistics"].get("videoCount")}

    def upload(self, mp4_path, meta):
        """Resumable upload, single PUT (files are <50MB). Unlisted-first."""
        size = mp4_path.stat().st_size
        init = requests.post(
            UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json"},
            json={
                "snippet": {
                    "title": meta["title"][:100],
                    "description": meta["description"][:4900],
                    "tags": meta.get("tags", [])[:15],
                    "categoryId": meta.get("category_id", "24"),
                },
                "status": {
                    "privacyStatus": meta.get("privacy", "unlisted"),
                    "selfDeclaredMadeForKids": False,
                    "embeddable": True,
                },
            }, timeout=60)
        init.raise_for_status()
        loc = init.headers["Location"]
        print(f"[yt] resumable session opened ({size/1e6:.1f}MB)")
        with open(mp4_path, "rb") as f:
            put = requests.put(loc, data=f,
                               headers={"Content-Type": "video/mp4"},
                               timeout=1800)
        put.raise_for_status()
        vid = put.json()["id"]
        print(f"[yt] uploaded -> https://youtu.be/{vid}")
        return vid

    def verify(self, video_id, wait_s=0):
        """Live verification — rule #1: not verified means broken.
        wait_s > 0 = retry loop: YouTube index/propagation can lag minutes
        after upload (a lag must NEVER abort the publish step)."""
        import time as _t
        deadline = _t.time() + wait_s
        while True:
            r = requests.get(f"{API}/videos", params={
                "part": "snippet,status,contentDetails", "id": video_id},
                headers={"Authorization": f"Bearer {self.token}"}, timeout=30)
            r.raise_for_status()
            items = r.json().get("items", [])
            if items:
                break
            if _t.time() >= deadline:
                raise RuntimeError(f"video {video_id} not found live!")
            print(f"[yt] not indexed yet — waiting 15s…")
            _t.sleep(15)
        v = items[0]
        v = items[0]
        return {"title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "privacy": v["status"]["privacyStatus"],
                "duration": v["contentDetails"]["duration"]}

    def set_privacy(self, video_id, privacy):
        r = requests.put(
            f"{API}/videos", params={"part": "status"},
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json"},
            json={"id": video_id,
                  "status": {"privacyStatus": privacy,
                             "selfDeclaredMadeForKids": False,
                             "embeddable": True}},
            timeout=30)
        r.raise_for_status()
        print(f"[yt] privacy -> {privacy}")
