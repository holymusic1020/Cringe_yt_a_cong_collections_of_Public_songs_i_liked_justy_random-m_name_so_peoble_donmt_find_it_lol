"""Karaoke word-captions (.ass) from timeline.json — +15-25% retention (research).

Layout: TOP-center, multi-line chunks (long speeches read naturally across
chunks with running word highlight). Narrator gets NO name-dot (explainer
voice). Final 2.6s = big end-card (punchy endings, boss request).
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

PAUSE_SPLIT = 0.55  # split chunk on natural speech pause


def _chunks(line):
    max_w = config.LAYOUT["max_chunk_words"]
    max_d = config.LAYOUT["max_chunk_dur"]
    words = line["words"]
    if not words:
        return []
    out, cur = [], [words[0]]
    for prev, w in zip(words, words[1:]):
        if (len(cur) >= max_w or w["start"] - prev["end"] > PAUSE_SPLIT
                or w["end"] - cur[0]["start"] > max_d):
            out.append(cur); cur = []
        cur.append(w)
    out.append(cur)
    return out


def _ass_color(hex_color):
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()  # ASS = &BBGGRR&


def _ts(t):
    hh = int(t // 3600); mm = int(t % 3600 // 60); ss = int(t % 60)
    return f"{hh}:{mm:02d}:{ss:02d}.{int(t % 1 * 100):02d}"


def build_ass(timeline_path, out_path, endcard="PART 2 TOMORROW"):
    tl = json.loads(Path(timeline_path).read_text())
    L = config.LAYOUT
    w, h = config.SHORT["w"], config.SHORT["h"]
    font_family, font_size = config.CAPTION_FONT_MAP.get(
        tl.get("lang", "en"), config.CAPTION_FONT_MAP["en"])
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kara,{font_family},{font_size},&H00FFFFFF,&H00B4B4B4,&H00202020,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,{L['caption_align']},{L['caption_margin_lr']},{L['caption_margin_lr']},{L['caption_margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for line in tl["lines"]:
        char = config.CAST[line["speaker"]]
        dot = "" if char.get("narrator") else \
            f"{{\\c{_ass_color(char['color'])}}}■{{\\c&HFFFFFF&}} "
        for chunk in _chunks(line):
            if not chunk:
                continue
            start, end = chunk[0]["start"], chunk[-1]["end"]
            text = "".join(
                "{\\k%d}%s " % (max(1, round((w_["end"] - w_["start"]) * 100)),
                                 w_["w"].upper())
                for w_ in chunk)
            events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Kara,,0,0,0,,"
                          f"{dot}{text.strip()}")

    # punchy end-card: big yellow center text, holds LONG enough to land
    if endcard:
        total = tl["total_s"]
        hold = config.LAYOUT.get("endcard_hold_s", 3.5)
        ec = (f"{{\\an5\\pos({w // 2},985)\\fs{L['endcard_font']}\\b1"
              f"\\fad(200,150)\\c&H3DD9FF&\\3c&H00202020}}{endcard}")
        events.append(f"Dialogue: 1,{_ts(max(0, total - hold))},{_ts(total - 0.1)},"
                      f"Kara,,0,0,0,,{ec}")

    Path(out_path).write_text(header + "\n".join(events) + "\n")
    print(f"[ass] {len(events)} events (incl end-card) -> {Path(out_path).name}")


if __name__ == "__main__":
    build_ass(sys.argv[1], sys.argv[2],
              sys.argv[3] if len(sys.argv) > 3 else "PART 2 TOMORROW")
