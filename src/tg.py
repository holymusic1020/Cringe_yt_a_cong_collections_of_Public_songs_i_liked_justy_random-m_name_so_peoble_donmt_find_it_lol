"""Telegram delivery — every finished video goes to the boss for review.
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. Absent -> warn + continue (no crash).
"""
import os, sys
from pathlib import Path

import requests  # lazy env-guard


def _creds():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return tok, chat


def send_message(text):
    tok, chat = _creds()
    if not tok or not chat:
        print("[tg] TELEGRAM_BOT_TOKEN/CHAT_ID not set — skipping message")
        return False
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      json={"chat_id": chat, "text": text},
                      timeout=30)
    ok = r.ok and r.json().get("ok")
    print(f"[tg] message {'sent' if ok else 'FAILED: ' + r.text[:200]}")
    return ok


def send_video(path, caption=""):
    """Bot API: videos up to 50MB. Fallback to document on 413."""
    tok, chat = _creds()
    if not tok or not chat:
        print("[tg] TELEGRAM_BOT_TOKEN/CHAT_ID not set — skipping video")
        return False
    path = Path(path)
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{tok}/sendVideo",
            data={"chat_id": chat, "caption": caption[:1000],
                  "supports_streaming": "true"},
            files={"video": (path.name, f, "video/mp4")}, timeout=600)
    if r.status_code == 413:
        with open(path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{tok}/sendDocument",
                data={"chat_id": chat, "caption": caption[:1000]},
                files={"document": (path.name, f, "video/mp4")}, timeout=600)
    ok = r.ok and r.json().get("ok")
    print(f"[tg] video {path.name} {'delivered ✅' if ok else 'FAILED: ' + r.text[:200]}")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 2:
        send_video(sys.argv[1], sys.argv[2])
    else:
        send_message("nixfav-engine: telegram channel wired ✅")
