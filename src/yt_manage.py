"""Manual YouTube video management (gated by yt_manage.yml dispatch only).
Actions: private | public | delete (delete requires confirm=DELETE).
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import requests
from yt import YT, API


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--action", choices=["private", "public", "delete"],
                    required=True)
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()

    yt = YT()
    ch = yt.whoami()
    print(f"[manage] channel: {ch['title']}")

    if args.action == "delete":
        if args.confirm != "DELETE":
            print("[manage] delete requires --confirm DELETE (safety gate)")
            sys.exit(2)
        r = requests.delete(f"{API}/videos", params={"id": args.video},
                            headers={"Authorization": f"Bearer {yt.token}"},
                            timeout=30)
        r.raise_for_status()
        print(f"[manage] DELETED {args.video}")
    else:
        yt.set_privacy(args.video, args.action)
        print(f"[manage] {args.video} -> {args.action} ✅")


if __name__ == "__main__":
    main()
