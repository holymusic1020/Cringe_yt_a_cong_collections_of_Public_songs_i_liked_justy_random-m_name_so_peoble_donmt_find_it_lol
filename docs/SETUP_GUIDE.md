# 📡 SETUP GUIDE — everything the boss needs to provide

*Do these in order. Everything is free. ~30 minutes total.*

---

## A. YouTube OAuth — the two-channel-safe recipe 📺

You have TWO channels on ONE Google account (NIX SPEECH o1 + NixSpeechFav).
**Each channel needs its own refresh token**, minted by picking that channel in
the account picker during authorization. One Google Cloud project + one OAuth
client serves both — so **reuse the o1 client if it still exists.**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) with that
   Google account → project dropdown (top bar):
   - If the **o1 project exists** (check APIs & Services → Credentials for an
     OAuth client) → open it. You can skip to step 3.
   - Else: **New Project** → name `nixfav-uploader` → create → select it.
2. **APIs & Services → Library → "YouTube Data API v3" → Enable.**
3. **OAuth consent screen** (left sidebar): External → app name `nixfav-uploader`
   → your emails. **Publish the app** (verify homepage link — your channel URL
   works). *Unpublished/testing apps die in 7 days — this bit us before.*
4. **Credentials → Create Credentials → OAuth client ID → Web application**
   (Web, NOT desktop — it has the redirect field):
   - Authorized redirect URI: `https://developers.google.com/oauthplayground`
   (exact, no trailing slash). Save **Client ID** + **Client Secret**.
5. Mint the NixSpeechFav refresh token:
   - Open [developers.google.com/oauthplayground](https://developers.google.com/oauthplayground)
   - ⚙️ gear (top right) → **"Use your own OAuth credentials"** → paste client
     ID + secret.
   - Left panel → tick BOTH scopes:
     `https://www.googleapis.com/auth/youtube.upload` and
     `https://www.googleapis.com/auth/youtube`
   - **Authorize** → sign in → **THE ACCOUNT PICKER WILL LIST YOUR CHANNELS** →
     ⚠️ **choose "Nix Speech Fav"** (NOT o1 — the token gets bound to whichever
     you pick!) → Allow.
   - **Exchange authorization code for tokens** → copy the **Refresh token**
     immediately (it's shown once).
6. That's it: `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` +
   `YOUTUBE_REFRESH_TOKEN` = bound to NixSpeechFav only. The preflight workflow
   will prove it by calling `channels.list mine=true` and printing the channel
   name — **verify before every battle** (Constitution §D).

**Gotchas:** trailing spaces in pasted secrets (we `.strip()` everything) · if
you accidentally pick the wrong channel: [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
→ remove the app → redo the Playground dance.

## B. Gemini API key(s) 🤖

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create
   API key → copy. Make **2 keys** if you can (rotation, playbook §6).
2. Names: `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`.

## C. (Optional but recommended) Pexels API key 🎞️

Free 30-second signup at [pexels.com/api](https://www.pexels.com/api/) →
`PEXELS_API_KEY`. Unlocks the satisfying/ASMR background library. Without it the
engine falls back to AI-generated animated backgrounds (still great, zero deps).

## D. How to hand me the keys safely 🔐

Drop them in a one-time paste (ctxt.io like last time) — I vault them straight
into **GitHub repo secrets** via the API (sealed with the repo's public key),
never into files, never into git history, never echoed back. The chat paste
self-expires; GitHub stores them encrypted; I only ever read them back masked.

## E. While you're at it (channel warmup — Constitution §A) 📱

- [ ] Channel avatar + banner: **I'll generate a set** — pick from the samples
- [ ] Profile bio/about: fill from the **phone app**, by hand
- [ ] 1–3h of silence after any big account change
- [ ] Day-1 organic session: watch/like/comment in our niche from the app
- [ ] Day-2: **first Short posted manually from the app** (I'll prep a
      "manual-first-post.mp4" ready in the workspace for exactly this)
- [ ] Day-3: automation attaches at 1/day (the engine handles the rest)

## F. What happens after you hand over the keys (me) 🤖

1. Vault all secrets → run **preflight** (green checkmarks or I fix until green)
2. Local full-pipeline render of Episode 1 → you approve the mp4
3. `workflow_dispatch` → **unlisted** test upload → verify live → you flip it
4. Enable the 06:05 UTC daily clock → engine takes over (1/day, jittered)
5. Daily receipt comments on the run summary; you check the dashboard whenever
