"""Preflight probe — verify before every battle, never pray (constitution §D).
Prints channel binding proof + secret sanity. Exits non-zero on any failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yt import YT


def main():
    print("== preflight: YouTube OAuth ==")
    yt = YT()
    ch = yt.whoami()
    print(f"   channel: {ch['title']} (id {ch['id']})")
    print(f"   subs: {ch['subs']} · videos: {ch['videos']}")
    if "fav" not in ch["title"].lower() and "nix" not in ch["title"].lower():
        print("   ⚠️ channel name doesn't look like NixSpeechFav — CHECK BINDING!")
        sys.exit(2)
    print("   binding ✅")
    print("== preflight: all good ==")


if __name__ == "__main__":
    main()
