"""Gemini 2.5 Flash TTS — the emotion engine (boss round-8: 'no emotions,
no natural feeling, doesn't know where to stop or breathe').

Style-directed synthesis: every line gets a persona + emotion direction
("You are Kamal, 55, a math teacher whose career just ended. Panic,
voice cracking, urgent pacing."). One call per line, no [beat] splitting —
the model breathes naturally at punctuation.

Rate limits: free tier is tight, so every call retries on 429/503 with
backoff. If Gemini is down entirely, callers fall back to edge-tts.
"""
import base64, json, os, subprocess, time, urllib.request
from pathlib import Path

API = ("https://generativelanguage.googleapis.com/v1beta/models/"
       "gemini-2.5-flash-preview-tts:generateContent")
MODEL_RPM_SAFETY = 12.0  # seconds between calls (free-tier friendly)


def have_key():
    return bool(os.environ.get("GEMINI_API_KEY_1", "").strip())


def _pcm_to_mp3(pcm_bytes, out_mp3):
    raw = str(out_mp3) + ".raw"
    Path(raw).write_bytes(pcm_bytes)
    p = subprocess.run(["ffmpeg", "-y", "-v", "error",
                        "-f", "s16le", "-ar", "24000", "-ac", "1",
                        "-i", raw, "-b:a", "48k", str(out_mp3)],
                       capture_output=True, text=True)
    Path(raw).unlink(missing_ok=True)
    if p.returncode != 0:
        raise RuntimeError(f"pcm->mp3 failed: {p.stderr[-200:]}")
    return out_mp3


def synth(text, voice, style, out_mp3, deadline_s=600):
    """One style-directed line -> mp3. Returns True on success.
    Falls back to a bare 'Read this line' prompt if a style trips the API."""
    prompts = []
    if style:
        prompts.append(f"{style}: {text}")
    prompts.append(f"Read this line with natural feeling: {text}")
    for pi, prompt in enumerate(prompts):
        if _post(prompt, voice, out_mp3, deadline_s, label=f"p{pi}"):
            return True
    return False


def _post(prompt, voice, out_mp3, deadline_s, label=""):
    key = os.environ["GEMINI_API_KEY_1"].strip()
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {
                "prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }).encode()
    t_start = time.time()
    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(
            API + "?key=" + key, data=body,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            b64 = (data["candidates"][0]["content"]["parts"][0]
                   ["inlineData"]["data"])
            _pcm_to_mp3(base64.b64decode(b64), out_mp3)
            # pacing so we never hammer the free tier
            time.sleep(MODEL_RPM_SAFETY)
            return True
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", "replace")[:250]
            except Exception:
                detail = ""
            msg = f"HTTP {e.code} {detail}"
            if e.code == 400:
                print(f"[gtts] {label} {voice}: 400 — {msg[:150]}")
                return False  # try next prompt variant
            retryable = e.code in (429, 500, 503)
            if retryable and time.time() - t_start < deadline_s:
                wait = min(40, 10 * attempt)
                print(f"[gtts] {voice} attempt {attempt} rate-limited — "
                      f"waiting {wait}s")
                time.sleep(wait)
                continue
            print(f"[gtts] {label} {voice} FAILED — {msg[:150]}")
            return False
        except Exception as e:
            print(f"[gtts] {label} {voice} {type(e).__name__}: {str(e)[:120]}")
            return False
