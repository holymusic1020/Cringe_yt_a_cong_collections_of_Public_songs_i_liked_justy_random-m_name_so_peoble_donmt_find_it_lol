# 🎬 nixfav-engine — AI story-video engine for @NixSpeechFav

Fully GitHub-Actions-native YouTube Shorts engine. No servers, no HF Space, no
keep-alive pingers. Every run: **generate → voice → visuals → render → upload →
commit state**. Free forever on a public repo (unlimited Actions minutes).

> Governed by `NEW_CHANNEL_CONSTITUTION.md` + `NEW_CHANNEL_PLAYBOOK.md`
> (source of truth — this engine implements their laws, it doesn't improvise).

## Architecture

```
GitHub Actions (ubuntu runner, public repo = unlimited min)
 ├─ post.yml       06:05 UTC daily → random delay 0–7200s → ONE short
 │                 (day-15/16 cadence flip adds the 12:00 slot automatically)
 ├─ preflight.yml  manual + daily probe: secrets sane? Gemini alive? YT token
 │                 refreshes? quota OK? state.json valid?  → verify, never pray
 └─ maint.yml      weekly prune of old artifacts + streak report issue

src/
 ├─ config.py      ALL tunables live here (clocks, delays, prompts, voice)
 ├─ state.py       state/state.json committed via GITHUB_TOKEN (no SQLite needed)
 ├─ story.py       Gemini story+hook+metadata (model fallback chain, dup-title guard)
 ├─ tts.py         edge-tts voiceover + word-boundary karaoke subtitles
 ├─ visuals.py     Pexels background loop (optional key) → FFmpeg-animated fallback
 ├─ music.py       incompetech CC-BY bed, energy-tagged, fades, credited in desc
 ├─ render.py      ffmpeg 1080×1920@30, veryfast crf22 (playbook §11 values)
 └─ upload.py      OAuth refresh → resumable upload → thumbnail, unlisted-first

state/state.json   cadence phase, posted titles, streak, backoff timestamps
```

## Constitution compliance map

| Law | Implementation |
|---|---|
| Fresh channel = 1/day, fixed clock | single 06:05 UTC cron, phase in state.json |
| Cadence flip day 15–16 (not 14) | `state.py` rolls random 15/16 at first run, persists |
| Random delay 0–7200s | `post.yml` sleep step before any API call |
| Never duplicate titles | `story.py` checks title vs all titles in state.json |
| Secrets in ONE vault, `.strip()`ed | GH repo secrets only; every read is `.strip()` |
| Preflight before every battle | `preflight.yml` gates first auto-post |
| No source audio / licensed music risk | 100% generated: TTS voice + CC-BY music bed |
| 30-min backoff after failed render | `state.json:last_render_fail` honored by post.yml |
| Verify live after deploy | post.yml prints video URL + yt-dlp probe of the upload |

## Secrets (repo → Settings → Secrets → Actions)

| Name | Notes |
|---|---|
| `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN` | playbook §7 recipe |
| `GEMINI_API_KEY_1` (…`_8` optional) | rotation, free @ aistudio |
| `PEXELS_API_KEY` *(optional)* | if absent → generated animated background |

## Phase plan

1. **Phase 0 (now)** — skeleton in this repo, niche prompts being finalized
2. **Phase 1** — first full pipeline run locally + `workflow_dispatch` test post
   (unlisted), you verify on YT
3. **Phase 2** — flip to public, 1/day for 15–16 days (constitution §A.6)
4. **Phase 3** — auto-flip to 2/day (06:05 + 12:05), long-form later

*Rule #1 of automation: if it's not verified live after deploy, it's broken.*
