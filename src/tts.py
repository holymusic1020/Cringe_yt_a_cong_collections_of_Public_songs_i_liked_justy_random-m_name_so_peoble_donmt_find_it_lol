"""Per-character TTS via edge-tts + word boundaries -> voiceover.mp3 + timeline.json.

HUMANIZING DELIVERY (boss spec: "voice too robotic — needs unexpected pauses,
long/short sounds"):
- scripts may write [beat] inside any line -> a natural 0.28-0.48s pause is
  inserted at that exact point (mid-sentence stops feel human)
- ellipses (…) and stretched spellings ("ohhh", "waaaait") also work —
  edge-tts interprets them naturally
- per-line emotion shifts rate/pitch on top of the character's base voice

timeline.json = [{speaker, start, end, text, words:[{w, start, end}]}]
Every downstream stage (captions, stickers, render, strict QA) reads this clock.
"""
import asyncio, json, random, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import time
import edge_tts
import gtts as gemini

_GEMINI_T0 = None
_GEMINI_SPENT = False

TICK = 1e7  # edge-tts offsets are 100ns ticks
GAP_S = 0.28  # breathing room between speakers


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {p.stderr[-500:]}")
    return p


def _dur(path):
    p = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "json", str(path)])
    return float(json.loads(p.stdout)["format"]["duration"])


def _silence(dur, path):
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
          "-t", f"{dur:.2f}", "-b:a", "48k", str(path)])


def _fade_edges(path, ms=35):
    """35ms fade in/out so [beat]-joined segments breathe instead of
    hard-cutting (boss: 'speech keeps stopping, no natural feeling')."""
    d = _dur(path)
    if d <= (ms / 1000) * 2.5:
        return path
    tmp = str(path) + ".faded.mp3"
    _run(["ffmpeg", "-y", "-i", str(path),
          "-af", f"afade=t=in:d={ms/1000},afade=t=out:st={d - ms/1000:.3f}:d={ms/1000}",
          "-b:a", "48k", tmp])
    Path(tmp).replace(path)
    return path


def _shift(base, delta, unit, clamp):
    """'+6%' + '+18%' -> '+24%'; '-2Hz' + '+25Hz' -> '+23Hz'"""
    b, d = int(base.rstrip(unit)), int(delta.rstrip(unit))
    v = max(-clamp, min(clamp, b + d))
    return f"{v:+d}{unit}"


async def _synth_line(text, voice, rate, pitch, out_path, fallback_voice=None):
    """3 attempts: same voice (transient hiccups), then narrator-voice
    fallback — a retired/flaky edge voice must NEVER kill an episode."""
    tries = [voice, voice, fallback_voice or voice]
    for attempt, v in enumerate(tries):
        words, audio = [], b""
        try:
            c = edge_tts.Communicate(text, v, rate=rate, pitch=pitch,
                                     boundary="WordBoundary")
            async for chunk in c.stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
                elif chunk["type"] == "WordBoundary":
                    words.append({"w": chunk["text"],
                                  "start": chunk["offset"] / TICK,
                                  "end": (chunk["offset"] + chunk["duration"]) / TICK})
            if not audio:
                raise RuntimeError("empty audio stream")
            out_path.write_bytes(audio)
            if v != voice:
                print(f"[tts]   ! {voice} unavailable -> fell back to {v}")
            return words
        except Exception as e:
            if attempt == len(tries) - 1:
                raise RuntimeError(f"TTS failed for all voices ({voice}, "
                                   f"{fallback_voice}): {e}") from e
            await asyncio.sleep(1.5)


def synth_episode(lines, workdir, lang="en"):
    """lines = [{speaker, text, emotion?}] -> (voice.mp3, timeline.json)."""
    workdir = Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    swaps = config.LANG_SWAPS.get(lang, {})
    timeline, per_line = [], []
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
        print(f"[tts] line {i + 1:02d} {sid:<8} -> {voice} "
              f"emo={line.get('emotion', 'neutral')}")
        raw = line["text"]
        emotion = line.get("emotion", "neutral")

        # ── GEMINI path (boss round-8: real emotion, natural breathing) ──
        # 12-min global budget: free-tier 429s can starve an episode, so
        # after the budget runs out the rest of the lines go to edge-tts
        # (an episode must ALWAYS complete and deliver).
        global _GEMINI_T0
        if (gemini.have_key() and sid in config.GEMINI_VOICES
                and not _GEMINI_SPENT):
            if _GEMINI_T0 is None:
                _GEMINI_T0 = time.time()
            elif time.time() - _GEMINI_T0 > 720:
                if not _GEMINI_SPENT:
                    print("[tts] gemini budget spent (12 min) — edge-tts "
                          "for remaining lines")
                    globals()["_GEMINI_SPENT"] = True
                _GEMINI_SPENT = True
            style = (f"You are {char['name']}, "
                     f"{config.GEMINI_PERSONA.get(sid, 'a lively character')}. "
                     f"{config.GEMINI_STYLE.get(emotion, config.GEMINI_STYLE['neutral'])}. "
                     "Perform this line for an animated story video. Breathe "
                     "naturally; pause where the punctuation says so. Say "
                     "ONLY the line, nothing else.")
            text_g = raw.replace("[beat]", "…")
            gmp3 = workdir / f"line_{i:02d}_g.mp3"
            print(f"[tts] line {i + 1:02d} {sid:<8} -> GEMINI "
                  f"{config.GEMINI_VOICES[sid]} emo={emotion}")
            if gemini.synth(text_g, config.GEMINI_VOICES[sid], style, gmp3):
                d = _dur(gmp3)
                toks = text_g.replace("…", " … ").split()
                toks = [w for w in toks if w != "…"]
                tot = sum(len(w) + 1 for w in toks) or 1
                cpos, line_words = 0.0, []
                for w in toks:
                    ws = cpos / tot * d
                    we = min(d, (cpos + len(w)) / tot * d)
                    line_words.append({"w": w,
                                       "start": round(t_cursor + ws, 3),
                                       "end": round(t_cursor + we, 3)})
                    cpos += len(w) + 1
                per_line.append([gmp3])
                timeline.append({
                    "speaker": sid, "name": char["name"],
                    "text": raw.replace("[beat] ", "").replace("[beat]", ""),
                    "start": round(t_cursor, 3), "end": round(t_cursor + d, 3),
                    "words": line_words,
                })
                t_cursor += d + GAP_S
                continue
            print(f"[tts] line {i + 1:02d} {sid:<8} gemini failed -> edge")

        segs = [s.strip() for s in raw.split("[beat]") if s.strip()]
        line_words, seg_cursor, entries = [], 0.0, []
        for k, seg in enumerate(segs):
            mp3 = workdir / f"line_{i:02d}_{k:02d}.mp3"
            fallback = swaps.get("narrator") or config.CAST["narrator"]["voice"]
            words = asyncio.run(_synth_line(seg, voice, rate, pitch, mp3,
                                           fallback_voice=fallback))
            _fade_edges(mp3)
            d = _dur(mp3)
            line_words += [{"w": w["w"],
                            "start": round(t_cursor + seg_cursor + w["start"], 3),
                            "end": round(t_cursor + seg_cursor + w["end"], 3)}
                           for w in words]
            entries.append(mp3)
            seg_cursor += d
            if k < len(segs) - 1:  # [beat] = humanizing mid-sentence pause
                gap = random.uniform(0.22, 0.36)
                sil = workdir / f"beat_{i:02d}_{k:02d}.mp3"
                _silence(gap, sil)
                entries.append(sil)
                seg_cursor += gap
        per_line.append(entries)
        timeline.append({
            "speaker": sid, "name": char["name"],
            "text": raw.replace("[beat] ", "").replace("[beat]", ""),
            "start": round(t_cursor, 3), "end": round(t_cursor + seg_cursor, 3),
            "words": line_words,
        })
        t_cursor += seg_cursor + GAP_S
    total = t_cursor

    sil = workdir / "sil.mp3"
    _silence(GAP_S, sil)
    rows = []
    for li, lst in enumerate(per_line):
        rows += [f"file '{e.name}'" for e in lst]
        if li < len(per_line) - 1:
            rows.append(f"file '{sil.name}'")
    (workdir / "concat.txt").write_text("\n".join(rows))
    voice_path = workdir / "voice.mp3"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
          str(workdir / "concat.txt"), "-c", "copy", str(voice_path)])

    (workdir / "timeline.json").write_text(json.dumps(
        {"total_s": round(total + 0.6, 2), "lang": lang, "lines": timeline},
        indent=1))
    print(f"[tts] {len(lines)} lines, {total:.1f}s voiceover, "
          f"{sum(len(t['words']) for t in timeline)} word boundaries, "
          f"{sum(1 for l in lines if '[beat]' in l['text'])} beat pauses")
    return voice_path, workdir / "timeline.json"


if __name__ == "__main__":
    ep = json.loads(Path(sys.argv[1]).read_text())
    synth_episode(ep["lines"], Path(sys.argv[2]), ep.get("lang", "en"))
