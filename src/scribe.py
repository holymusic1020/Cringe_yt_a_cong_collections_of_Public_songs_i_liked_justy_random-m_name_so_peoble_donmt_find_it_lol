"""THE SCRIBE — autonomous episode writer (round-14: full-lifetime automation).

Runs on GH Actions (scribe.yml, 2x/day). Keeps the queue >= KEEP episodes
deep: asks Gemini to write a new episode following EVERY channel law,
validates it hard, and commits only what passes. The conveyor (render ->
vault -> daily post) can then run unattended forever.

Language law is decided HERE, deterministically: every window of 7 episodes
must hold 5 EN + 1 BN + 1 HI. A queued BN/HI slot always outranks an open
arc continuation (the arc simply waits for the next EN slot).

Failure policy: never commit garbage, never go red — alert Telegram and
retry next run. A dry queue for one day beats a bad episode forever.
"""
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import tg

QUEUE = config.ROOT / "scripts" / "queue"
KEEP = 4          # generate while unrendered depth < this
MAX_PER_RUN = 2   # gentle on the free tier
EMOTIONS = {"angry", "deadpan", "excited", "neutral", "panic", "sad",
            "shock", "smug", "whisper"}
BG_CATS = {"school": ("classroom", "school", "student", "exam", "chalk", "hallway"),
           "food": ("food", "cooking", "kitchen", "canteen", "street food", "samosa"),
           "working": ("worker", "labor", "construction", "job", "build", "office"),
           "city": ("city", "street", "traffic", "night", "urban", "scooter", "market"),
           "satisfying": ("satisfying", "slime", "paint", "craft", "soap", "sand")}


def _scripts():
    """All real episode scripts, ordered by number."""
    out = []
    for p in QUEUE.glob("ep*.json"):
        m = re.fullmatch(r"ep(\d+)\.json", p.name)
        if m:
            out.append((int(m.group(1)), p))
    return sorted(out)


def _depth():
    return sum(1 for _, p in _scripts() if not p.with_suffix(".done").exists())


def _next_lang():
    """5 EN / 1 BN / 1 HI in every 7 — deterministic from queue history."""
    langs = [json.loads(p.read_text()).get("lang", "en") for _, p in _scripts()[-6:]]
    if "bn" not in langs:
        return "bn"
    if "hi" not in langs:
        return "hi"
    return "en"


LANG_NAME = {"en": "English", "bn": "Bengali (Bangla)", "hi": "Hindi"}
LANG_DIRECTIVE = {
    "en": "LANGUAGE: write everything in natural, everyday English.",
    "bn": ("LANGUAGE: write EVERY line — and the title — in Bengali, Bangla "
           "script (\u09ac\u09be\u0982\u09b2\u09be). NEVER romanize, never English sentences. "
           "Modern loanwords (laptop, phone) allowed. An emoji in the title "
           "is fine."),
    "hi": ("LANGUAGE: write EVERY line — and the title — in Hindi, Devanagari "
           "script (\u0939\u093f\u0902\u0926\u0940). NEVER romanize, never Hinglish, never English "
           "sentences. Modern loanwords (laptop, phone) allowed. An emoji in "
           "the title is fine."),
}


def _cast_line():
    parts = []
    for sid, c in config.CAST.items():
        if c.get("narrator"):
            continue
        parts.append(f"{sid} ({c.get('role', '?')})")
    return ", ".join(parts)


def _arc_context(lang):
    """Find the newest UNRESOLVED promise in queue history (an endcard that
    promises a next part/FINALE which no later same-arc script delivered) and
    continue THAT arc — viewer promises must be kept. Language must match."""
    scripts = _scripts()
    eps = [(n, json.loads(p.read_text())) for n, p in scripts]
    for i in range(len(eps) - 1, -1, -1):
        n, ep = eps[i]
        if ep.get("lang", "en") != lang:
            continue
        end = (ep.get("endcard") or "").upper()
        if not ("FINALE" in end or "PART" in end or "TOMORROW" in end):
            continue
        arc = ep.get("arc")
        resolved = any(later.get("arc") == arc and later.get("part", 1) > ep.get("part", 1)
                       for _, later in eps[i + 1:])
        if resolved:
            continue
        prev = (f"An earlier episode '{ep['title']}' (arc '{arc}', part "
                f"{ep.get('part', 1)}) ended on the card \"{ep.get('endcard')}\" "
                f"and the channel still owes viewers that episode. Its final "
                f"spoken line: \"{ep['lines'][-1]['text'][:140]}\".")
        if "FINALE" in end:
            return (f"{prev} Write the promised FINALE of this arc: full "
                    f"resolution, the twist explained, satisfying ending. "
                    f"part={ep.get('part', 1) + 1}, arc='{arc}'.", ep)
        return (f"{prev} Write the NEXT PART of this arc: escalate the stakes, "
                f"end mid-tension on another cliffhanger. part="
                f"{ep.get('part', 1) + 1}, arc='{arc}'.", ep)
    return "Start a fresh 2-3 part story arc (different vibe from recent eps).", None


def _prompt(lang, arc_directive):
    return f"""You write scripts for "Nix Speech Fav" — a YouTube Shorts channel
of animated multi-character story episodes (Zack-D.-Films style: hook in the
first second, fast pace, twist endings, relatable everyday drama).

CAST (fixed universe, use these speaker ids): {_cast_line()}
Also available: narrator (the robot host — speaks little, deadpan glue).

{LANG_DIRECTIVE[lang]}
TITLE: punchy, under 90 characters, hook-style, one emoji allowed.

STORY LAWS (all mandatory):
- FIRST line is a CHARACTER (never narrator) shouting a hook that grabs in 1 second.
- 12 to 14 lines total. Each line 60-160 characters — full dramatic
  sentences, not quick quips. The finished episode must run ~100 seconds.
- Sprinkle "[beat]" inside lines for dramatic pauses (at least 8 total) — edge-tts turns them into real pauses.
- Topics: all of life — school, family, money, neighbors, tech, suspicion,
  mildly-naughty mischief. NEVER extreme, never gore, never politics.
- Insults must SOUND like insults. Emotions: {', '.join(sorted(EMOTIONS))}.
- {arc_directive}
- endcard: short all-caps card for the last seconds (e.g. "PART 3 TOMORROW" or "FINALE: <the reveal>").
- bg_hints: 2-3 short phrases matching ONE of: school / food / working / city / satisfying.
- energy: "low", "mid" or "high".

OUTPUT: pure JSON only, no markdown fences, exactly this shape:
{{"title": "...", "topic": "...", "arc": "...", "part": 1, "lang": "{lang}",
  "energy": "high", "endcard": "...", "bg_hints": ["...", "..."],
  "lines": [{{"speaker": "riku", "emotion": "panic", "text": "..."}}]}}"""


_WORKS = None  # (api_version, model) that answered — cached per run


def _candidates(key):
    """Ranked text-model candidates from Google's live list + static
    fallbacks. Model names AND api-version aliases drift (gemini-2.5-flash
    listed under v1beta but 404s there — resolved via v1); the Scribe tries
    them all and remembers what works. Never dies of a rename."""
    url = ("https://generativelanguage.googleapis.com/v1beta/models?key=" + key
           + "&pageSize=100")
    models = []
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            models = [m["name"].split("/")[-1]
                      for m in json.loads(r.read()).get("models", [])
                      if "generateContent" in m.get("supportedGenerationMethods",
                                                    ["generateContent"])]
    except Exception as e:
        print(f"[scribe] model list failed ({e}) — using static fallbacks")
    bad = ("tts", "image", "native", "lite", "thinking", "embedding", "audio",
           "vision", "exp", "aide")
    good = [m for m in models
            if "flash" in m and not any(b in m for b in bad)]
    ranked = sorted(good, key=lambda m: (m.startswith("gemini-2"), len(m)),
                    reverse=True)
    return (ranked + ["gemini-flash-latest", "gemini-2.0-flash"])[:4]


def _gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY_1", "").strip()
    if not key:
        raise RuntimeError("no GEMINI_API_KEY_1")
    global _WORKS
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 1.05}})
    tries = [_WORKS] if _WORKS else         [(v, m) for v in ("v1beta", "v1") for m in _candidates(key)]
    last = "no attempt"
    for ver, model in tries:
        url = (f"https://generativelanguage.googleapis.com/{ver}/models/"
               f"{model}:generateContent?key=" + key)
        req = urllib.request.Request(url, data=body.encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            _WORKS = (ver, model)
            print(f"[scribe] answered by {ver}/{model}")
            return d["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            last = f"{ver}/{model}: {e.code} {e.read()[:160]!r}"
            print(f"[scribe] {last}")
    raise RuntimeError(f"no working Gemini endpoint ({last})")


def _validate(ep, existing_titles):
    def bad(msg):
        return ValueError(msg)
    for k in ("title", "topic", "arc", "lang", "energy", "endcard",
              "bg_hints", "lines", "part"):
        if k not in ep:
            raise bad(f"missing field {k}")
    if not (15 <= len(ep["title"]) <= 100):
        raise bad("title length")
    if ep["title"] in existing_titles:
        raise bad("duplicate title")
    if ep["lang"] not in ("en", "bn", "hi"):
        raise bad("lang")
    if ep["energy"] not in ("low", "mid", "high"):
        raise bad("energy")
    lines = ep["lines"]
    if not (12 <= len(lines) <= 14):
        raise bad(f"{len(lines)} lines")
    if lines[0]["speaker"] == "narrator":
        raise bad("opens with narrator (hook law)")
    beats = 0
    for l in lines:
        if l["speaker"] not in config.CAST:
            raise bad(f"unknown speaker {l['speaker']}")
        if l["emotion"] not in EMOTIONS:
            raise bad(f"unknown emotion {l['emotion']}")
        if not (60 <= len(l["text"]) <= 160):
            raise bad("line length")
        beats += l["text"].count("[beat]")
    if beats < 8:
        raise bad(f"only {beats} [beat]s (need >=8)")
    chars = sum(len(l["text"]) for l in lines)
    est_s = chars / 13 + beats * 0.38 + len(lines) * 0.28
    if est_s < 92:
        # boss law: episodes >= 90s (gemini-3 wrote a 73s episode Sep 25)
        raise bad(f"estimated only {est_s:.0f}s runtime ({chars} chars)")
    hints = " ".join(ep["bg_hints"]).lower()
    if not ep["bg_hints"] or not any(k in hints for cat in BG_CATS.values() for k in cat):
        raise bad("bg_hints match no category")
    # language script sanity
    text = " ".join(l["text"] for l in lines)
    if ep["lang"] == "bn":
        assert_ok = sum(1 for ch in text if "\u0980" <= ch <= "\u09FF") > len(text) * 0.4
    elif ep["lang"] == "hi":
        assert_ok = sum(1 for ch in text if "\u0900" <= ch <= "\u097F") > len(text) * 0.4
    else:
        assert_ok = sum(1 for ch in text if ch.isascii() or ch in "…—") > len(text) * 0.9
    if not assert_ok:
        raise bad(f"text is not {ep['lang']}")
    return True


def _commit(path):
    for cmd in (["git", "config", "user.name", "nixfav-engine"],
                ["git", "config", "user.email", "engine@users.noreply.github.com"]):
        subprocess.run(cmd, check=True)
    subprocess.run(["git", "add", str(path)], check=True)
    subprocess.run(["git", "commit", "-m",
                    f"scribe: {path.stem} written by AI [skip ci]"], check=True)
    p = subprocess.run(["git", "push"])
    if p.returncode != 0:
        subprocess.run(["git", "pull", "--rebase", "origin",
                        os.environ.get("GITHUB_REF_NAME", "main")], check=False)
        subprocess.run(["git", "push"], check=True)


def main():
    made = 0
    while _depth() < KEEP and made < MAX_PER_RUN:
        lang = _next_lang()
        arc_directive, prev = _arc_context(lang)
        prompt = _prompt(lang, arc_directive)
        ep = None
        for attempt in (1, 2, 3):
            try:
                raw = _gemini(prompt)
                raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.M).strip()
                cand = json.loads(raw)
                titles = {json.loads(p.read_text())["title"] for _, p in _scripts()}
                _validate(cand, titles)
                ep = cand
                break
            except Exception as e:
                print(f"[scribe] attempt {attempt} rejected: {e}")
                time.sleep(20)
        if ep is None:
            tg.send_message("✍️ Scribe: generation failed validation twice — "
                            "queue not topped up this run. Depth now "
                            f"{_depth()}. Will retry next run.")
            break
        num = (_scripts()[-1][0] + 1) if _scripts() else 1
        path = QUEUE / f"ep{num:03d}.json"
        path.write_text(json.dumps(ep, indent=1, ensure_ascii=False) + "\n")
        try:
            _commit(path)
        except Exception as e:
            path.unlink(missing_ok=True)
            subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
            print(f"[scribe] commit failed: {e}")
            break
        print(f"[scribe] WROTE {path.name}: {ep['title']} ({ep['lang']}, "
              f"{len(ep['lines'])} lines, arc '{ep['arc']}' part {ep['part']})")
        made += 1
    print(f"[scribe] done — queue depth {_depth()} (target >= {KEEP}), wrote {made}")


if __name__ == "__main__":
    main()
