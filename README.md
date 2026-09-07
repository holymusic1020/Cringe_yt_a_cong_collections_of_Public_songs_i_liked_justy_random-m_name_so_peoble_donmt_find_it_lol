# 🎬 NixSpeechFav Engine — AI character-story Shorts factory

**Concept:** satisfying/gameplay background → a recurring **named cast of 25+
characters** (family, friends, school) each with their **own voice + animated
sticker that pops in when they speak** → karaoke word-captions → serialized
multi-part stories with cliffhangers → mostly English, ~1 Bangla + 1 Hindi
episode per week.

**Runs 100% on GitHub Actions** (public repo = unlimited free minutes). No
servers, no keep-alive, no cost. Every run: generate → voice → render →
upload → verify → commit state.

📖 **Read the strategy docs first:**
[`docs/RESEARCH.md`](docs/RESEARCH.md) ·
[`docs/CAST_UNIVERSE.md`](docs/CAST_UNIVERSE.md) ·
[`docs/FEATURES_BRAINSTORM.md`](docs/FEATURES_BRAINSTORM.md) ·
[`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)

## Pipeline

```
post.yml (daily 06:05 UTC + 0–2h human jitter)
 ├─ slot check      → state/state.json (cadence 15/16d roll, backoff laws)
 ├─ story.py        → Gemini: cast-aware episode + cliffhanger + metadata
 │                    (model fallback chain, dup-title guard, canon memory)
 ├─ tts.py          → edge-tts per-character voices (300+, incl bn-BD/hi-IN)
 │                    + word boundaries → karaoke .ass captions
 ├─ visuals.py      → bg layer (generated / no-copyright gameplay / Pexels)
 │                    + character stickers pop-in per speaking turn
 ├─ music.py        → incompetech CC-BY bed, energy-matched, fades, credited
 ├─ render.py       → ffmpeg 1080×1920@30 veryfast crf22 (playbook §11)
 ├─ upload.py       → OAuth refresh → resumable upload (unlisted-first)
 ├─ verify.py       → live probe of the uploaded video (rule #1)
 └─ state_commit.py → state + canon committed via GITHUB_TOKEN

preflight.yml (daily 00:10 UTC + on demand) — secrets/Gemini/YT/quota probe
maint.yml (weekly) — artifact prune + streak report
```

## Secrets (Settings → Secrets → Actions)

`YOUTUBE_CLIENT_ID` · `YOUTUBE_CLIENT_SECRET` · `YOUTUBE_REFRESH_TOKEN`
(bound to **NixSpeechFav** via account-picker — see SETUP_GUIDE §A) ·
`GEMINI_API_KEY_1` (+`_2`…`_8` rotation) · `PEXELS_API_KEY` *(optional)*

## Constitution compliance

Fixed daily clock + random delay (§C) · 1/day fresh-channel cadence with
15–16d roll (§A.6) · secrets in one vault, stripped (§D) · preflight before
every battle (§D) · CC-BY music only, credited (§3) · never duplicate titles ·
30-min render backoff · unlisted-first upload + live verify · anti-template
variation engine (2025 "inauthentic content" policy shield).

*Rule #1 of automation: if it's not verified live after deploy, it's broken.*
