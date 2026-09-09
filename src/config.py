"""ALL tunables in one place — constitution & playbook values.
Voice IDs validated against live `edge-tts --list-voices` (Sep 2026, 324 voices).
BG priority per boss directive: REAL VIDEO first, generated images = plan C only."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# ── Clock & cadence (constitution §C, playbook §1) ─────────────────────────
SHORT_SLOT_UTC = "06:05"           # fixed daily clock, off the :00 mark
SECOND_SLOT_UTC = "12:05"          # activates after cadence flip
RANDOM_DELAY_RANGE_S = (0, 7200)   # shorts: 0-2h jitter
CADENCE_FLIP_DAYS = (15, 16)       # roll once, persist, never re-roll
RENDER_BACKOFF_S = 30 * 60         # 30 min backoff after failed render
LANG_WHEEL = ["en", "en", "en", "en", "en", "bn", "hi"]  # 5 EN / 1 BN / 1 HI

# ── Video (playbook §2 & §11 + 2026 retention research) ────────────────────
SHORT = dict(w=1080, h=1920, fps=30, target_s=100, min_s=85, max_s=115)
X264 = dict(preset="veryfast", crf="22")

# ── The Cast (fixed names/voices/faces = channel brand) ────────────────────
# rate/pitch per character = same base voice can feel different people.
# color = caption + nametag accent per character (visual identity, anti-template)
# narrator=True -> no sticker, no name-dot: pure explainer voice
CAST = {
    "narrator":dict(name="Narrator",       voice="en-US-EmmaMultilingualNeural", rate="-4%",  pitch="-2Hz",  color="#CFD8DC", role="explainer", narrator=True),
    "nix":     dict(name="Nix",           voice="en-US-AndrewNeural",           rate="+6%",  pitch="+0Hz",  color="#FFD93D", role="protagonist"),
    "lubna":   dict(name="Lubna (Mom)",   voice="en-US-MichelleNeural",         rate="+2%",  pitch="+0Hz",  color="#1FBF75", role="mom"),
    "rafiq":   dict(name="Rafiq (Dad)",   voice="en-US-ChristopherNeural",      rate="-4%",  pitch="-2Hz",  color="#4D96FF", role="dad"),
    "tuli":    dict(name="Tuli (Sis)",    voice="en-US-AriaNeural",             rate="+8%",  pitch="+4Hz",  color="#FF6B9D", role="big sis"),
    "milli":   dict(name="Milli",         voice="en-US-AnaNeural",              rate="+10%", pitch="+8Hz",  color="#FF9F45", role="little sis"),
    "nani":    dict(name="Nani",          voice="en-US-AvaNeural",              rate="-12%", pitch="-6Hz",  color="#B088F9", role="grandma"),
    "dada":    dict(name="Dada",          voice="en-US-EricNeural",             rate="-8%",  pitch="-4Hz",  color="#8B9DC3", role="grandpa"),
    "jamal":   dict(name="Jamal Chacha",  voice="en-US-GuyNeural",              rate="+3%",  pitch="+0Hz",  color="#F9C80E", role="rich uncle"),
    "phupu":   dict(name="Phupu Shaheen", voice="en-US-JennyNeural",            rate="+12%", pitch="+3Hz",  color="#FF6B6B", role="gossip aunt"),
    "riku":    dict(name="Riku",          voice="en-US-RogerNeural",            rate="+9%",  pitch="+2Hz",  color="#43D8A9", role="gamer cousin"),
    "mr_haque": dict(name="Mr. Haque",     voice="hi-IN-MadhurNeural",           rate="+0%",  pitch="+0Hz",  color="#7FB069", role="neighbor uncle"),
    "mrs_haque":dict(name="Mrs. Haque",    voice="hi-IN-SwaraNeural",            rate="+5%",  pitch="+0Hz",  color="#E07BE0", role="neighbor aunty"),
    "joy":     dict(name="Joy",           voice="en-US-BrianNeural",            rate="+5%",  pitch="+0Hz",  color="#6BCB77", role="best friend 1"),
    "ding":    dict(name="Ding",          voice="en-US-BrianMultilingualNeural",rate="+2%",  pitch="+15Hz", color="#9B8CFF", role="best friend 2"),
    "mira":    dict(name="Mira",          voice="en-US-EmmaNeural",             rate="+0%",  pitch="+0Hz",  color="#FFD6A5", role="crush"),
    "mim":     dict(name="Mim",           voice="en-GB-LibbyNeural",            rate="+4%",  pitch="+0Hz",  color="#FF8FAB", role="girlfriend"),
    "kamal":   dict(name="Sir Kamal",     voice="en-GB-RyanNeural",             rate="-3%",  pitch="-2Hz",  color="#5C946E", role="math teacher"),
    "ruiz":    dict(name="Madam Ruiz",    voice="en-GB-SoniaNeural",            rate="+7%",  pitch="+2Hz",  color="#C74B9E", role="english teacher"),
    "huda":    dict(name="Principal Huda",voice="en-GB-MaisieNeural",           rate="-5%",  pitch="-3Hz",  color="#37474F", role="principal"),
    "sam":     dict(name="Sam",           voice="en-US-AndrewMultilingualNeural",rate="+8%", pitch="+10Hz", color="#A0C4FF", role="snitch"),
    "bruno":   dict(name="Bruno",         voice="en-GB-ThomasNeural",           rate="-6%",  pitch="-8Hz",  color="#E63946", role="bully"),
    "choto":   dict(name="Choto Mia",     voice="en-IN-PrabhatNeural",          rate="+0%",  pitch="+0Hz",  color="#F4A261", role="canteen boss"),
    "osman":   dict(name="Driver Osman",  voice="en-US-SteffanNeural",          rate="-10%", pitch="-2Hz",  color="#83C5BE", role="bus driver"),
    "preity":  dict(name="Miss Preity",   voice="en-IN-NeerjaNeural",           rate="+6%",  pitch="+0Hz",  color="#FFC6FF", role="tutor"),
    "browser": dict(name="Browser",       voice=None,                            rate="+0%",  pitch="+0Hz",  color="#C9A66B", role="dog (SFX only)"),
}
CORE_FAMILY = ["nix", "lubna", "rafiq", "tuli", "milli", "nani", "dada"]
HAS_STICKER = ["nix", "lubna", "rafiq", "tuli", "milli", "nani", "dada",
               "bruno", "huda"]  # cast art expands over time

# Bangla / Hindi episode voice swaps (same characters, native voices)
LANG_SWAPS = {
    "bn": {"nix": "bn-BD-PradeepNeural", "lubna": "bn-BD-NabanitaNeural",
           "narrator": "bn-IN-TanishaaNeural"},
    "hi": {"nix": "hi-IN-MadhurNeural", "lubna": "hi-IN-SwaraNeural",
           "mira": "hi-IN-NeerjaNeural", "narrator": "hi-IN-SwaraNeural"},
}

# ── Emotion engine: per-line emotion shifts rate/pitch on top of base voice ─
# (kept moderate — big pitch swings make male voices sound female, boss bug report)
EMOTIONS = {
    "neutral": ("+0%",  "+0Hz"),
    "angry":   ("+14%", "+12Hz"),
    "shock":   ("+8%",  "+20Hz"),
    "sad":     ("-16%", "-12Hz"),
    "excited": ("+18%", "+10Hz"),
    "smug":    ("-8%",  "-4Hz"),
    "whisper": ("-22%", "-6Hz"),
    "panic":   ("+22%", "+12Hz"),
    "deadpan": ("-12%", "-6Hz"),
}

# ── Layout (1080x1920): captions TOP multi-line, sticker BIG bottom-left ────
LAYOUT = dict(
    sticker_w=560,              # character stickers
    sticker_x=24,               # true bottom-left
    sticker_bottom_gap=44,      # small gap under, no dead space
    caption_font=74,
    caption_align=8,            # top-center
    caption_margin_v=320,       # lower from top edge (boss: not glued to top)
    caption_margin_lr=90,
    max_chunk_words=7,
    max_chunk_dur=2.8,
    endcard_font=104,
    endcard_hold_s=3.5,
)

# caption font per language (files live in assets/fonts; names = font families)
CAPTION_FONT_MAP = {
    "en": ("Luckiest Guy", 80),
    "hi": ("Mukta", 84),
    "bn": ("Hind Siliguri", 84),
}

# ── The Robot — NixSpeechFav mascot narrator (MAIN character of the channel) ─
ROBOT = dict(
    sid="narrator",
    w=600,                      # mascot is slightly bigger than characters
    x=24, bottom_gap=40,
    bob_px=13, bob_period_s=2.7,       # idle floating
    blink_period_s=3.7, blink_dur_s=0.14,  # eyes-open/blink frame swap
    slide_px=320, slide_s=0.22,        # slide-in from below (all stickers)
    talk_flicker_period_s=0.34,        # antenna vibration WHILE TALKING:
    talk_flicker_on_s=0.17,            # open/tilt frame swap every 0.17s
    jaw_bob_px=3.5,                    # jaw motion = head bob at speech tempo
    jaw_bob_period_s=0.16,             # (no visible mouth — boss law)
)

# ── Story topic pool — ALL of life, randomized (boss law: never one theme) ──
TOPICS = [
    "school drama", "bullying & payback", "racism confronted", "family chaos",
    "sibling wars", "friendship betrayal", "crush embarrassment", "karma stories",
    "exam disasters", "neighbor drama", "wedding chaos", "travel disaster",
    "first job", "sports tryouts", "talent show", "secrets & mystery",
    "money lessons", "food adventures", "technology chaos", "growing up",
    "festival madness", "rich vs poor moments", "teachers & students",
    "street smarts", "loss & lessons", "parties gone wrong", "small victories",
]

# ── Backgrounds — REAL VIDEO FIRST (boss law), generated = plan C ──────────
BG_PRIORITY = ["pexels_video", "nocopyright_gameplay", "generated_image"]

# energy -> what kind of real video matches the story vibe
BG_ENERGY_MAP = {
    "chaos":  "gameplay",   # parkour / racing / fast
    "high":   "gameplay",
    "mid":    "satisfying",
    "chill":  "satisfying", # asmr / paint / cutting / restock
}
PEXELS_QUERIES = {
    "satisfying": [
        "paint mixing", "kinetic sand cutting", "soap cutting", "glass cutting",
        "hydraulic press", "restocking pantry", "pressure washing",
        "cake decorating", "lathe machining", "piping frosting",
    ],
    "gameplay": ["minecraft parkour", "racing game gameplay"],
}
# free-use gameplay channels (credit in description — we always credit)
NOCOPYRIGHT_SOURCES = [
    dict(video_id="sjA9VVfZYgk", credit="Governare NCG", kind="minecraft_parkour"),
    dict(video_id="85z7jqGAGcc", credit="Orbital NCG", kind="minecraft_parkour"),
]
BG_CREDIT = {
    "pexels_video": "Background footage: Pexels (free license)",
    "nocopyright_gameplay": "Background gameplay: {credit} (free-use)",
    "generated_image": None,
}

# ── Music (playbook §3 — CC-BY only, credited) ─────────────────────────────
MUSIC_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{name}.mp3"
MUSIC = {
    "The Descent": "mid", "Darkest Child": "low", "Volatile Reaction": "high",
    "Rising Game": "mid", "Achilles": "high", "Five Armies": "high",
}
MUSIC_CREDIT = "Music: {name} — Kevin MacLeod (incompetech.com) — CC BY 4.0"
MUSIC_VOLUME = 0.12          # bed under voiceover, never overpowering
FADE_IN_S, FADE_OUT_S = 3.0, 4.0

# ── Story engine ────────────────────────────────────────────────────────────
EPISODE_SPEC = dict(
    duration_s=(35, 55),
    hook_first_line_max_words=8,     # cold-open law: first line stops the scroll
    speakers_per_episode=(2, 4),     # from CORE_FAMILY in v1
    cliffhanger=True,
    cta_rotation=[
        "Follow for Part 2 👀",
        "Like if this made you smile — subscribe for Part 2 🔔",
        "Comment what Nix should do next 👇 (Part 2 drops tomorrow)",
        "Subscribe — you already watched this far 😌",
    ],
)
SERIES = dict(
    enabled=True,
    max_parts=3,
    end_card_text="PART {n} TOMORROW 🎬",
)

# ── Gemini (playbook §6) ────────────────────────────────────────────────────
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "flash-latest"]
GEMINI_KEYS = ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2"]
DUPE_SUFFIXES = [" - Reloaded", " | Final Round", " 2", " 3"]

# ── Upload (playbook §7) ────────────────────────────────────────────────────
YT_CATEGORY_ID = "24"  # Entertainment
UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YT_READ_SCOPE = "https://www.googleapis.com/auth/youtube"
CHANNEL_URL = "https://www.youtube.com/@NixSpeechFav"
DEFAULT_PRIVACY = "unlisted"   # unlisted-first, flip public after live verify
