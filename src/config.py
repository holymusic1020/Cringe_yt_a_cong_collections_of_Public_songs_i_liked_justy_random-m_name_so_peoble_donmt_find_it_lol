"""ALL tunables in one place — constitution & playbook values, nothing hardcoded elsewhere."""

# ── Clock & cadence (constitution §C, playbook §1) ─────────────────────────
SHORT_SLOT = "06:05 UTC"          # fixed daily clock, off the :00 mark
SECOND_SLOT = "12:05 UTC"         # activates after cadence flip
RANDOM_DELAY_RANGE_S = (0, 7200)  # shorts: 0-2h, never post at :00 sharp
CADENCE_FLIP_DAYS = (15, 16)      # roll 15 OR 16 once, persist, never re-roll
RENDER_BACKOFF_S = 30 * 60        # 30 min backoff after failed render

# ── Video (playbook §2 & §11) ──────────────────────────────────────────────
SHORT = dict(w=1080, h=1920, fps=30, target_s=38, min_s=20, max_s=45)
X264 = dict(preset="veryfast", crf="22")

# ── Story engine (niche: interesting / funny / cringe story shorts) ────────
STORY_STYLE = {
    "vibes": ["interesting", "funny", "cringe", "revenge", "karma", "facepalm"],
    "length_words": (120, 150),   # ~40s at typical TTS pace
    "hook_first_line": True,      # first 3 words must stop the scroll
    "language": "en",
}
TTS_VOICE = "en-US-ChristopherNeural"  # final voice = your pick after audition
TTS_RATE = "+8%"                       # slightly hot, story pace

# ── Music (playbook §3 — never carry licensed audio) ───────────────────────
MUSIC = {
    "The Descent": "mid",
    "Darkest Child": "low",
    "Volatile Reaction": "high",
    "Rising Game": "mid",
    "Achilles": "high",
    "Five Armies": "high",
}
MUSIC_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{name}.mp3"
MUSIC_CREDIT = "Music: {name} — Kevin MacLeod (incompetech.com) — CC BY 4.0"

# ── Gemini (playbook §6 — model names retire, keep a chain) ────────────────
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "flash-latest"]
GEMINI_KEYS = ["GEMINI_API_KEY_1"]  # extend to _2.._8 for rotation
DUPE_SUFFIXES = [" - Reloaded", " | Final Round", " 2", " 3"]

# ── Upload (playbook §7) ───────────────────────────────────────────────────
YT_CATEGORY_ID = "24"  # Entertainment (story niche) — flip to 20 if gaming
UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YT_READ_SCOPE = "https://www.googleapis.com/auth/youtube"
