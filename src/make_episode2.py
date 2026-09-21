"""Episode pipeline v2 (from-scratch rebuild, round-12).

Usage: python3 src/make_episode2.py scripts/queue/ep009.json [out.mp4]

Flow: TTS (edge/gemini+breaker) -> multi-clip bg -> one-pass engine render
-> DELIVERY GATE (per-line frame audit of the actual output) -> Telegram
-> junk law -> .done marker. Nothing ships unaudited.
"""
import json, random, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from tts import synth_episode
from ass import build_ass
from bgbuild import build_bg
import engine
sys.path.insert(0, str(config.ROOT / "scripts"))
import tg

QUEUE = config.ROOT / "scripts" / "queue"


def pick_script():
    cands = [p for p in sorted(QUEUE.glob("ep*.json"))
             if not p.with_suffix(".done").exists()]
    if not cands:
        raise RuntimeError("queue empty")
    return cands[0]


def main():
    if len(sys.argv) > 1:
        script = Path(sys.argv[1])
    else:
        try:
            script = pick_script()
        except RuntimeError:
            print("[make] queue empty — conveyor caught up, nothing to render")
            sys.exit(0)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        config.ROOT / "output" / f"{script.stem}.mp4"
    ep = json.loads(script.read_text())
    t0 = time.time()
    # RESUME: a workdir that already has voice+captions+bg skips TTS/bg
    # (crashed renders must not re-pay 4 minutes of network TTS)
    workdir = None
    need = ("voice.mp3", "timeline.json", "captions.ass", "bg.mp4", "bg_source.mp4")
    for c in sorted((config.ROOT / ".work").glob(f"{script.stem}_*"), reverse=True):
        if all((c / f).exists() for f in need):
            workdir = c
            break
    resume = workdir is not None
    if not resume:
        workdir = config.ROOT / ".work" / f"{script.stem}_{int(time.time())}"
        workdir.mkdir(parents=True, exist_ok=True)

    if resume:
        tl = json.loads((workdir / "timeline.json").read_text())
        voice = str(workdir / "voice.mp3")
        print(f"[make] RESUME {workdir.name}: voiceover {tl['total_s']:.0f}s "
              f"+ captions + multi-clip bg already built")
    else:
        voice, timeline = synth_episode(ep["lines"], workdir, ep.get("lang", "en"))
        tl = json.loads(Path(timeline).read_text())
        print(f"[make] voiceover {tl['total_s']:.0f}s")

        endcard = ep.get("endcard", "PART 2 TOMORROW")
        build_ass(timeline, workdir / "captions.ass", endcard)

        bg = build_bg(ep.get("bg_hints"), tl["total_s"] + 0.5, workdir / "bgwork")
        shutil.copy(bg, workdir / "bg.mp4")
        shutil.copy(bg, workdir / "bg_source.mp4")

    out.parent.mkdir(parents=True, exist_ok=True)
    engine.render(workdir, out)

    # ── DELIVERY GATE: audit the exact file that ships ──
    r = subprocess.run(["python3", str(config.ROOT / "scripts" / "audit_video.py"),
                        str(out), str(workdir / "timeline.json"),
                        str(workdir / "bg_source.mp4")],
                       cwd=config.ROOT)
    assert r.returncode == 0, "delivery gate REFUSED — not sending"

    # metadata + sidecars
    desc = [ep["title"], "",
            f"Part {ep.get('part', 1)} of the '{ep.get('arc', 'standalone')}' "
            "story. New episodes daily!", "",
            "Characters are AI-animated. Subscribe and join the NixFam 🤖"]
    (out.parent / f"{out.stem}_meta.json").write_text(json.dumps({
        "title": ep["title"], "description": "\n".join(desc),
        "tags": [t for t in ep.get("topic", "").split() if len(t) > 3][:8]
                + ["shorts", "story", "animation", "nixfav"],
        "category_id": config.YT_CATEGORY_ID, "duration_s": tl["total_s"],
        "privacy": config.DEFAULT_PRIVACY, "src": out.name,
        "arc": ep.get("arc"), "part": ep.get("part", 1)}, indent=1))
    shutil.copy(workdir / "timeline.json", out.parent / f"{out.stem}_timeline.json")
    shutil.copy(workdir / "bg_source.mp4", out.parent / f"{out.stem}_bg.mp4")

    caption = f"🎬 {ep['title']}\n{tl['total_s']:.0f}s · {ep.get('topic', '')}"
    tg.send_video(out, caption)

    Path(script).with_suffix(".done").write_text(out.name)
    shutil.rmtree(workdir, ignore_errors=True)

    # junk law: only this episode's trio (+bg sidecar) in output/
    keep = {out.name, f"{out.stem}_meta.json", f"{out.stem}_timeline.json",
            f"{out.stem}_bg.mp4"}
    for f in out.parent.iterdir():
        if f.is_file() and f.name not in keep and f.suffix in (".mp4", ".json"):
            f.unlink(missing_ok=True)
    print(f"[make] {out.name} COMPLETE in {time.time() - t0:.0f}s "
          f"({tl['total_s']:.0f}s episode, audited + delivered)")


if __name__ == "__main__":
    main()
