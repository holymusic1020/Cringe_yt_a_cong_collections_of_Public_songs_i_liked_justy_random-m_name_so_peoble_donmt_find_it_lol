"""Episode orchestrator: script JSON -> TTS -> captions -> bg -> render -> Telegram.

Usage:
  python src/make_episode.py scripts/queue/ep001.json [out.mp4]
  python src/make_episode.py            # picks oldest unrendered from queue/

Rendered marker: a .done sidecar next to the script (queue is consumed FIFO).
Vault rule (playbook §0): always keep ≥1 rendered episode ahead of the slot.
"""
import json, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config, tg
from tts import synth_episode
from ass import build_ass
import bg
from render import render

QUEUE = config.ROOT / "scripts" / "queue"


def pick_script():
    cands = [p for p in sorted(QUEUE.glob("ep*.json"))
             if not p.with_suffix(".done").exists()]
    if not cands:
        raise RuntimeError("queue empty — every script has a .done marker")
    return cands[0]


def main():
    script = Path(sys.argv[1]) if len(sys.argv) > 1 else pick_script()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        config.ROOT / "output" / f"{script.stem}.mp4"
    ep = json.loads(script.read_text())
    workdir = Path("/tmp/ep_work")

    t0 = time.time()
    voice, timeline = synth_episode(ep["lines"], workdir, ep.get("lang", "en"))
    tl = json.loads(timeline.read_text())
    if not (config.SHORT["min_s"] - 15 <= tl["total_s"] <= config.SHORT["max_s"] + 15):
        print(f"[make] WARNING: {tl['total_s']:.0f}s outside target "
              f"{config.SHORT['min_s']}-{config.SHORT['max_s']}s (still rendering)")
    endcard = ep.get("endcard")
    if not endcard:  # CTA rotation fallback
        import random
        endcard = random.choice(config.EPISODE_SPEC["cta_rotation"])
    build_ass(timeline, workdir / "captions.ass", endcard)

    bgvid, bgcredit = bg.fetch_bg(ep.get("energy", "mid"),
                                  tl["total_s"] + 0.5, workdir / "bgwork")
    shutil.copy(bgvid, workdir / "bg.mp4")

    out.parent.mkdir(parents=True, exist_ok=True)
    render(workdir, out)

    # YouTube description preview (dup-title guard + credits assembled later by upload.py)
    desc_bits = [b for b in [bgcredit] if b]
    caption = f"🎬 {ep['title']}\n{tl['total_s']:.0f}s · {ep.get('topic','')}"
    if desc_bits:
        caption += "\n" + " | ".join(desc_bits)
    tg.send_video(out, caption)

    script.with_suffix(".done").write_text(out.name)
    print(f"[make] {out.name} DONE in {time.time()-t0:.0f}s "
          f"({tl['total_s']:.0f}s episode, {len(ep['lines'])} lines)")


if __name__ == "__main__":
    main()
