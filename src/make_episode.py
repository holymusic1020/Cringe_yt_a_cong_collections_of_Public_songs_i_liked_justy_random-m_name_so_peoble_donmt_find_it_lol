"""Episode orchestrator: script JSON -> TTS -> captions -> bg -> HAND OFF.

Stage 1 (this file): synth everything render needs, then os.execv into
postrender.py — replacing this process image so ALL edge-tts/aiohttp residue
is freed before ffmpeg passes start (sandbox memory cap assassinates ffmpeg
otherwise — battle-scarred fact).

Usage:
  python src/make_episode.py scripts/queue/ep001.json [out.mp4]
  python src/make_episode.py            # oldest unrendered from queue/
"""
import json, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from tts import synth_episode
from ass import build_ass
import bg

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
    # NEVER /tmp — it's a 993MB tmpfs (RAM!) and OOM-kills ffmpeg mid-pass
    workdir = config.ROOT / ".work" / f"{script.stem}_{int(time.time())}"
    workdir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    voice, timeline = synth_episode(ep["lines"], workdir, ep.get("lang", "en"))
    tl = json.loads(timeline.read_text())
    print(f"[make] voiceover {tl['total_s']:.0f}s "
          f"(target {config.SHORT['min_s']}-{config.SHORT['max_s']}s)")

    endcard = ep.get("endcard")
    if not endcard:
        import random
        endcard = random.choice(config.EPISODE_SPEC["cta_rotation"])
    build_ass(timeline, workdir / "captions.ass", endcard)

    bgvid, bgcredit = bg.fetch_bg(ep.get("energy", "mid"),
                                  tl["total_s"] + 0.5, workdir / "bgwork")
    shutil.copy(bgvid, workdir / "bg.mp4")

    out.parent.mkdir(parents=True, exist_ok=True)
    # hand off EVERYTHING stage 2 needs (fresh process, clean heap)
    job = {"script": str(script), "out": str(out), "workdir": str(workdir),
           "ep": ep, "total_s": tl["total_s"], "bgcredit": bgcredit}
    (workdir / "job.json").write_text(json.dumps(job))
    print(f"[make] stage 1 done in {time.time()-t0:.0f}s — execv to postrender")
    os.execv(sys.executable, [sys.executable,
                              str(config.ROOT / "src" / "postrender.py"),
                              str(workdir)])


import os  # (top of file ordering for execv readability)

if __name__ == "__main__":
    main()
