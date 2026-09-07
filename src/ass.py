"""Karaoke word-captions (.ass) from timeline.json — +15-25% retention (research).
Words grouped into caption chunks (≤4 words / ≤1.8s / speaker change / long pause).
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

MAX_WORDS, MAX_DUR, PAUSE_SPLIT = 4, 1.8, 0.55


def _chunks(line):
    words = line["words"]
    if not words:
        return []
    out, cur = [], [words[0]]
    for prev, w in zip(words, words[1:]):
        if (len(cur) >= MAX_WORDS or w["start"] - prev["end"] > PAUSE_SPLIT
                or w["end"] - cur[0]["start"] > MAX_DUR):
            out.append(cur); cur = []
        cur.append(w)
    out.append(cur)
    return out


def _ass_color(hex_color):
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()  # ASS = &BBGGRR&


def build_ass(timeline_path, out_path):
    tl = json.loads(Path(timeline_path).read_text())
    w, h = config.SHORT["w"], config.SHORT["h"]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kara,DejaVu Sans,84,&H00FFFFFF,&H5AFFFFFF,&H00202020,&H90000000,-1,0,0,0,100,100,1,0,1,6,0,2,80,80,640,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for line in tl["lines"]:
        color = _ass_color(config.CAST[line["speaker"]]["color"])
        for chunk in _chunks(line):
            if not chunk:
                continue
            start, end = chunk[0]["start"], chunk[-1]["end"]
            def ts(t):
                hh = int(t // 3600); mm = int(t % 3600 // 60); ss = int(t % 60)
                return f"{hh}:{mm:02d}:{ss:02d}.{int(t % 1 * 100):02d}"
            text = "".join(
                "{\\k%d}%s " % (max(1, round((w_["end"] - w_["start"]) * 100)),
                                 w_["w"].upper())
                for w_ in chunk)
            # name-dot: speaker-colored ■ leading the chunk
            text = f"{{\\c{color}}}■{{\\c&HFFFFFF&}} " + text.strip()
            events.append(f"Dialogue: 0,{ts(start)},{ts(end)},Kara,,0,0,0,,{text}")
    Path(out_path).write_text(header + "\n".join(events) + "\n")
    print(f"[ass] {len(events)} caption chunks -> {Path(out_path).name}")


if __name__ == "__main__":
    build_ass(sys.argv[1], sys.argv[2])
