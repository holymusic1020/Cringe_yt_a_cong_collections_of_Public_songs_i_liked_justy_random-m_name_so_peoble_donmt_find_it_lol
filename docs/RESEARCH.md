# 🔬 DEEP RESEARCH — AI Character-Story Shorts (Sep 2026)

*Research phase for @NixSpeechFav. Sources cited inline. Directional stats from
tool-vendor blogs are marked as such — treated as signal, not gospel.*

---

## 1. The format is validated (and then some)

**"Dual-stimulation" shorts** — satisfying/gameplay background + story narration
+ captions — are a proven high-completion format. Vendors literally sell this as
a product: story content over Minecraft parkour reports ~378% higher completion
than text-only (vendor claim, directional) — [hooked.so](https://www.hooked.so/tools/minecraft-parkour-video),
[revid.ai](https://www.revid.ai/tools/minecraft-parkour-video), [short.ai](https://www.short.ai/minecraft-parkour-video).
The psychology: the bg feeds the dopamine-hungry part of the brain while the
story carries the narrative — [r/ADHD discussion](https://www.reddit.com/r/ADHD/comments/12abibo/why_do_those_tik_toks_with_minecraft_and_subway/).

**Character-driven AI drama is hot right now**: "Part 3 | The Billionaire Who
Chose Us" style AI storytime pulls 700K+ likes on TikTok; "He Said, She Said"
two-sides animated stories and character POV skits are trending tags —
[TikTok #drama-storytime](https://www.tiktok.com/discover/drama-storytime),
[#storytimewithcharacter](https://www.tiktok.com/discover/tik-tok-trend-story-time-with-character).

**The whitespace nobody owns:** parkour-bg tools use *generic narration*; AI
drama channels use *static captions*. **No one combines: a fixed recurring named
cast → each character with its own voice + animated sticker that pops in when
they speak → serialized multi-part stories → EN/BN/HI mix → satisfying bg.**
That combo is our moat AND our policy shield (see §2).

## 2. YouTube policy 2025→2027 (the rules of the road)

- **Jul 15, 2025:** "repetitious content" renamed **"inauthentic content"** —
  mass-produced, templated, minimal-variation videos are demonetizable. AI tools
  are NOT banned; AI-assisted content with original storytelling + human
  creativity stays fully monetizable —
  [policy breakdown](https://www.auditsocials.com/blog/youtube-inauthentic-content-policy-2026-mass-produced-ai-generated-monetization-creators-brands),
  [milx](https://milx.app/en/trends/should-you-use-ai-generated-videos-and-how-will-it-impact-youtube-monetization),
  [supertone](https://www.supertone.ai/en/work/youtube-ai-monetization-policy-2025-eng).
- **What gets flagged:** same template, same situation over and over, slideshows
  with no narrative. **What stays safe:** original scripts, evolving storylines,
  variation, entertainment value. → *Our recurring cast must live in DIFFERENT
  stories each episode — the cast is the brand, not the template.*
- **AI disclosure labels:** required only for *realistic* synthetic media (real
  people doing fake things, altered real events). Cartoon characters = "clearly
  fantastical" → **no label required** — [rules decoded](https://monetizednow.com/youtube-ai-content-monetization-policy).
  Per our Constitution §C we'll still note "AI-assisted" in descriptions.
- ⚠️ **Feb 1, 2027 deadline:** YPP thresholds for NEW applicants rise to
  8,000 watch-hours/365d or **20M Shorts views/90d** (from today's 1k subs +
  10M Shorts views/90d or 4k hours) — [source](https://monetizednow.com/youtube-ai-content-monetization-policy).
  → **Strategy: treat Oct–Dec 2026 as the monetization push window.**

## 3. Shorts algorithm benchmarks 2026 (what we engineer for)

| Metric | Target | Source |
|---|---|---|
| Held through first 3s | >80% (50–60% of all drop-off happens here) | [humbleandbrag](https://humbleandbrag.com/blog/youtube-shorts-benchmarks), [opus.pro](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention) |
| Midpoint retention | >60% | [humbleandbrag](https://humbleandbrag.com/blog/youtube-shorts-benchmarks) |
| Average % viewed (APV) | >70% — *the* ranking metric for Shorts | [humbleandbrag](https://humbleandbrag.com/blog/youtube-shorts-benchmarks) |
| Best length for STORY format | **40–60s (highest avg views tier)**; comedy 18–28s | [virvid](https://virvid.ai/blog/best-shorts-length-retention-2026), [opus.pro](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention) |
| Burned-in captions | +15–25% retention (mandatory for us) | [opus.pro](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention) |
| Hook law | Open at the most dramatic moment, zero preamble | [virvid](https://virvid.ai/blog/best-shorts-length-retention-2026) |

→ Episode spec updated: **35–55s**, cold-open hook, karaoke word-captions,
cliffhanger + "Part 2" end-card in the final 3s.

## 4. Voice stack (free, keyless, multilingual)

**edge-tts** (MIT, no API key, 300+ neural voices) — includes **Bangladesh
Bangla** `bn-BD-NabanitaNeural` (F) / `bn-BD-PradeepNeural` (M), full Hindi and
English catalogs — [voice samples](https://www.oceanz.site/en/explore/edge-tts),
[edge-tts guide](https://offlinetts.com/blog/self-hosted-tts-guide-2026/).
Enough distinct voices for a 25+ character cast with per-language swaps.
**Fallbacks if Microsoft locks it down:** Kokoro-82M (Apache-2.0, CPU, pip),
Piper (MIT) — [comparison](https://offlinetts.com/blog/self-hosted-tts-guide-2026/).
Word-boundary events → perfect karaoke caption timing for free.

## 5. Background sourcing (copyright-safe layers, best → good)

1. **Generated bg** (zero copyright risk): AI stills + Ken Burns motion, or
   procedural FFmpeg scenes. Infinite, unique per episode (policy-friendly).
2. **"No Copyright Gameplay" channels** (e.g. [Governare NCG](https://www.youtube.com/watch?v=sjA9VVfZYgk),
   [2h parkour pack](https://www.youtube.com/watch?v=85z7jqGAGcc)) — creators
   grant free-use for bg purposes; credit them in description (we will).
3. **Pexels/Pixabay** satisfying & ASMR b-roll (free license).
4. **Later:** record our own MC gameplay = 100% ours + extra content stream.
   Layered with original story+voices = transformative use, commentary-style —
   the monetizable pattern per policy §2.

## 6. Two channels, one Google account (OAuth answer)

Each YouTube channel (brand account) needs its **own refresh token** minted via
the account picker: during OAuth, Google lists all channels on the account —
**select NixSpeechFav specifically** → that refresh token is bound to that
channel only; `channels.list mine=true` then returns NixSpeechFav —
[SO: brand accounts via OAuth](https://stackoverflow.com/questions/41016537/youtube-apis-access-mutiple-youtube-channels-brand-accounts-using-google-adm),
[SO: per-channel auth](https://stackoverflow.com/questions/77941797/youtube-api-channels-list-returns-only-account-channel-but-does-not-list-re),
[matrix ops guide](https://woodyrush.com/en/blog/youtube-oauth-setup-guide/).
One GCP project + one OAuth client serves ALL channels. We can **reuse the o1
client** if it's on the same Google account — full walkthrough in SETUP_GUIDE.

## 7. Language strategy (your 5 EN / 1 BN / 1 HI weekly mix)

- EN = reach engine; BN/HI = loyalty + underserved niches with cheaper attention.
- Same cast, native voices (bn-BD / hi-IN edge-tts) — the characters are
  language-agnostic. BN episodes can lean local humor (Dhaka life = your edge).
- Track separately from day 1: if BN episodes overperform EN on APV → spin a
  dedicated BN channel later (Constitution B: separate vessel).

## 8. Launch calendar (constitution-compliant)

| When | What |
|---|---|
| Day 0–2 | Profile art (generated), manual app-first post, organic touches |
| Day 3–17 | 1 Short/day @ 06:05 UTC +0–2h jitter (automation attaches) |
| Day 18+ | 2/day (auto cadence flip on rolled day 15/16) |
| Day 30+ | Long-form every 2d (best-of compilations w/ chapter intros) |
| Oct–Dec 2026 | Monetization push BEFORE Feb 2027 threshold hike |
