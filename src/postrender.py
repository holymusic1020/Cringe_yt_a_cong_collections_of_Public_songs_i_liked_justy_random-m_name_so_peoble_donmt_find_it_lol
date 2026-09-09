"""Stage 2 (fresh process via execv): render + metadata + telegram + marker.
Runs with a clean heap — ffmpeg passes get all the memory they need.
"""
import json, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config, tg
from render import render


def main():
    workdir = Path(sys.argv[1])
    job = json.loads((workdir / "job.json").read_text())
    ep, out = job["ep"], Path(job["out"])

    t0 = time.time()
    render(workdir, out)

    desc_lines = [
        ep["title"], "",
        f"Part {ep.get('part', 1)} of the '{ep.get('arc', 'standalone')}' story. "
        "New episodes daily!", "",
        "Characters are AI-animated. Subscribe and join the NixFam 🤖",
    ]
    if job.get("bgcredit"):
        desc_lines += ["", job["bgcredit"]]
    meta = {
        "title": ep["title"],
        "description": "\n".join(desc_lines),
        "tags": [t for t in ep.get("topic", "").split() if len(t) > 3][:8]
                + ["shorts", "story", "animation", "nixfav"],
        "category_id": config.YT_CATEGORY_ID,
        "duration_s": job["total_s"],
        "privacy": config.DEFAULT_PRIVACY,
        "src": out.name,
        "arc": ep.get("arc"), "part": ep.get("part", 1),
    }
    (out.parent / f"{out.stem}_meta.json").write_text(json.dumps(meta, indent=1))

    caption = f"🎬 {ep['title']}\n{job['total_s']:.0f}s · {ep.get('topic', '')}"
    if job.get("bgcredit"):
        caption += "\n" + job["bgcredit"]
    shutil.copy(workdir / "timeline.json", out.parent / f"{out.stem}_timeline.json")
    tg.send_video(out, caption)

    Path(job["script"]).with_suffix(".done").write_text(out.name)
    shutil.rmtree(workdir, ignore_errors=True)  # disk hygiene

    # JUNK LAW (boss): only the LATEST episode's files may live in output/ —
    # older mp4s/metas/timelines get purged so the latest is always findable
    keep = {out.name,
            (out.parent / f"{out.stem}_meta.json").name,
            (out.parent / f"{out.stem}_timeline.json").name}
    for f in out.parent.iterdir():
        if f.is_file() and f.name not in keep and f.suffix in (".mp4", ".json"):
            f.unlink(missing_ok=True)
    print(f"[post] junk law enforced: output/ now holds only {sorted(keep)}")

    print(f"[post] {out.name} COMPLETE in {time.time()-t0:.0f}s "
          f"({job['total_s']:.0f}s episode)")


if __name__ == "__main__":
    main()
