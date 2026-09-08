# 🗺️ ROADMAP V2 — "Zack-D-grade machine" (research + boss directives fused)

*Sep 8 2026 · This is the plan the boss approved: research-first, story-first,
video-bgs-first. Execute in order after boss says "c".*

---

## 1. STORY ENGINE V2 (the #1 priority — "stories fine but not as interesting as I hoped")

**Formula (Zack D. Films decoded + boss rules):**
1. **Hook = strange question / crisis in the first 1–2 seconds** (no intro, no greeting, no "hey guys" — ever)
2. **Conflict stated in ONE line** immediately after
3. **Escalation ladder** — every 8–12s a new complication or reveal (micro-drama pacing)
4. **Mildly naughty / suspicious / cringe seasoning** — boyfriend-girlfriend tension, caught-sneaking, secret phones, "who did it" mysteries. NEVER explicit: no nudity-adjacent, no heavy violence, nothing an advertiser would flee from. Rule: "naughty enough to gossip about, clean enough to watch at school lunch."
5. **SERIOUS-MOMENT CLIFFHANGER ENDINGS** (boss law): end mid-crisis on the most dramatic line — e.g. the door opens and it's *her*. Endcard shrinks to a small "PART 2 →" badge, never a cheerful goodbye.
6. **Twist/loop bonus** (Zack-D): final line circles back to the opening question when the arc closes.

**Arc queue v2 (to write after "c"):**
- Arc 2 — **"The Missing Exam Paper"** (mystery: paper stolen from Sir Kamal's desk; everyone's a suspect; Ep1 ends: Nix finds it… IN HIS OWN BAG 😱)
- Arc 3 — **"The Phone At The Wedding"** (naughty-tame: cousin Riku films something he shouldn't have; blackmail chaos; serious endings)
- Arc 4 — **"The New Neighbor"** (suspicious: why does Mr. Haque's garage light up at 3 a.m. every night?)
- Arc 5 — **"The Crush Confession"** (cringe/naughty: Mira's note lands in the WRONG hands)
- BN/HI episodes: 5 EN / 1 BN / 1 HI weekly wheel (unchanged)

**Automation:** `story.py` (Gemini) writes to a per-arc outline the boss can
edit in the queue JSONs; hand-written scripts remain the gold standard until
the model earns trust. Dup-title guard + canon memory (past events fed back).

## 2. BACKGROUND = REAL VIDEO ALWAYS (Zack-D lesson: visual quality = legitimacy in 2s)

- **Pexels primary** (key now in secrets ✅): 20 satisfying queries incl. pipe
  painting, spray painting, tile cutting, pressure washing, hydro dipping +
  parkour/racing gameplay queries
- No-copyright gameplay channels = fallback (flaky from datacenter IPs)
- Generated Ken Burns = plan C emergency only
- **v2.1 (after launch):** bg SWITCHES at story beats (calm → chaos), cut on
  the escalation ladder timestamps from the timeline
- **v2.2:** occasional Zack-D-style "visual reveal" moments — AI-generated
  insert image (the stolen paper, the 3 a.m. garage) shown as a 2s punch-in

## 3. VISUALS (fixed this session)

- ✅ Vanishing-sticker bug KILLED (comma escaping) — strict per-window QA now
  runs on EVERY GitHub render (`scripts/qa_strict.py` → workflow fails loudly)
- ✅ Captions lowered (margin 320), solid-gray karaoke pre-highlight (clear
  two-tone), new fonts: **Luckiest Guy** (EN), **Mukta** (HI), **Hind Siliguri**
  (BN) — chunky shorts-display typography
- ✅ Robot v2: sleeker glossy-black visor design (smarter look, boss request)
- Next: robot "talk" mouth animation variant (3rd frame: visor waveform) —
  after "c"; sticker idle sway for characters

## 4. VOICE (the last big gap — "robotic, no emotions")

- Step 1 (now): edge-tts with emotion shaping (live)
- Step 2 (after "c"): **Gemini TTS style-directed voices** — per-line style
  prompts ("say it like a smug bully mocking a smaller kid") → real acting.
  `tts.py` gets a GEMINI path with edge-tts fallback per line (never blocks)
- Step 3 (if needed): self-hosted CosyVoice for the hero characters

## 5. UPLOAD + CADENCE (keys are in — build after "c")

- `preflight.py`: refresh token → `channels.list mine=true` → must print
  "Nix Speech Fav" (proves the account-picker binding) → quota check
- `upload.py`: unlisted upload → yt-dlp live verify → flip public
- `post.yml`: **1 Short every 15–19h** (randomized window, boss spec) fed from
  the artifact vault (FIFO), dup-title guard against state
- First posts: the three Biryani arc episodes (re-rendered with new engine)

## 6. CONSTITUTION COMPLIANCE (unchanged laws)

Fixed clock ± jitter · secrets vaulted · verify-live-or-it's-broken ·
never hammer providers · 30-day patience window before judging (§E numbers-day)

---

**Execution order after "c":** preflight+upload modules → verify YT binding →
re-render Biryani arc on new engine → first scheduled post → story.py v2 +
Arc 2 → Gemini TTS voices → bg switching. 🤖
