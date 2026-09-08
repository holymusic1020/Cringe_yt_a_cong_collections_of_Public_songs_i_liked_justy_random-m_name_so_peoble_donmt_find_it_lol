"""Per-character TTS via edge-tts + word boundaries -> voiceover.mp3 + timeline.json.

timeline.json = [{speaker, start, end, text, words:[{w, start, end}]}]
Every downstream stage (captions, stickers, render) reads this one clock.
"""
import asyncio, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import edge_tts

TICK = 1e7  # edge-tts offsets are 100ns ticks
GAP_S = 0.28  # breathing room between speakers (feels human, not machine-gun)


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {p.stderr[-500:]}")
    return p


def _dur(path):
    p = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "json", str(path)])
    return float(json.loads(p.stdout)["format"]["duration"])


def _shift(base, delta, unit, clamp):
    """'+6%' + '+18%' -> '+24%'; '-2Hz' + '+25Hz' -> '+23Hz'"""
    b, d = int(base.rstrip(unit)), int(delta.rstrip(unit))
    v = max(-clamp, min(clamp, b + d))
    return f"{v:+d}%".replace("%", unit) if unit == "Hz" else f"{v:+d}%"


async def _synth_line(text, voice, rate, pitch, out_path):
    words, audio = [], b""
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch,
                             boundary="WordBoundary")
    async for chunk in c.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            words.append({"w": chunk["text"],
                          "start": chunk["offset"] / TICK,
                          "end": (chunk["offset"] + chunk["duration"]) / TICK})
    out_path.write_bytes(audio)
    return words


def synth_episode(lines, workdir, lang="en"):
    """lines = [{speaker, text, emotion?}] -> (voice.mp3, timeline.json)."""
    workdir = Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    swaps = config.LANG_SWAPS.get(lang, {})
    timeline, parts = [], []
    t_cursor = 0.15
    for i, line in enumerate(lines):
        sid = line["speaker"]
        char = config.CAST[sid]
        voice = swaps.get(sid, char["voice"])
        if voice is None:
            raise RuntimeError(f"{sid} has no voice (SFX-only character)")
        emo_rate, emo_pitch = config.EMOTIONS.get(
            line.get("emotion", "neutral"), config.EMOTIONS["neutral"])
        rate = _shift(char["rate"], emo_rate, "%", clamp=50)
        pitch = _shift(char["pitch"], emo_pitch, "Hz", clamp=60)
        mp3 = workdir / f"line_{i:02d}.mp3"
        words = asyncio.run(_synth_line(
            line["text"], voice, rate, pitch, mp3))
        d = _dur(mp3)
        timeline.append({
            "speaker": sid, "name": char["name"], "text": line["text"],
            "start": round(t_cursor, 3), "end": round(t_cursor + d, 3),
            "words": [{"w": w["w"], "start": round(t_cursor + w["start"], 3),
                       "end": round(t_cursor + w["end"], 3)} for w in words],
        })
        parts.append(mp3)
        t_cursor += d + GAP_S
    total = t_cursor

    # silence gap file matched to edge-tts mp3 format (24kHz mono)
    sil = workdir / "sil.mp3"
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
          "-t", str(GAP_S), "-b:a", "48k", str(sil)])
    lst = workdir / "concat.txt"
    rows = []
    for i, p in enumerate(parts):
        rows.append(f"file '{p.name}'")
        if i < len(parts) - 1:
            rows.append(f"file '{sil.name}'")
    lst.write_text("\n".join(rows))
    voice_path = workdir / "voice.mp3"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
          "-c", "copy", str(voice_path)])

    # 0.4s head + 1.0s tail so the last word + CTA don't clip
    (workdir / "timeline.json").write_text(json.dumps(
        {"total_s": round(total + 0.6, 2), "lang": lang, "lines": timeline},
        indent=1))
    print(f"[tts] {len(lines)} lines, {total:.1f}s voiceover, "
          f"{sum(len(t['words']) for t in timeline)} word boundaries")
    return voice_path, workdir / "timeline.json"


if __name__ == "__main__":
    ep = json.loads(Path(sys.argv[1]).read_text())
    synth_episode(ep["lines"], Path(sys.argv[2]), ep.get("lang", "en"))
