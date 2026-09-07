# 🧠 BRAINSTORM — features, ranked by impact × effort

*S = build into v1 · A = fast-follow (week 1–2) · B = growth phase · C = moonshot*

## S-tier (v1 — the engine ships with these)

1. **Karaoke word-captions** (edge-tts word boundaries, ASS \k tags) — +15–25%
   retention, non-negotiable per research.
2. **Character pop-in system** — speaker's sticker slides in + name tag + their
   voice; previous speaker fades. The signature look of the channel.
3. **Multi-part auto-serialization** — Gemini writes "Part 1 (cliffhanger)" →
   engine schedules Part 2 next slot → end-card "Part 2 tomorrow 👀" → episode
   numbering in titles ("Ep 7 · Part 2"). Chain-viewing by design.
4. **Cold-open hook law** — script MUST start at the most dramatic moment;
   enforced in the prompt + linted (first line ≤ 8 words).
5. **CTA rotation** — like/subscribe lines rotate (never identical outro =
   anti-template + anti-dup-title).
6. **Tri-lingual scheduler** — 5 EN / 1 BN / 1 HI weekly wheel, per config.
7. **Anti-inauthentic engine** — per-episode: unique story seed, unique bg
   combination, varied caption color scheme per character, dup-title guard.
8. **State + canon commit** — every upload commits state.json + canon events.
9. **Preflight probe workflow** — secrets, Gemini, YT refresh, quota — before
   every battle (constitution D).
10. **Fixed clock + human jitter** — 06:05 UTC + 0–2h random delay (§C).

## A-tier (fast follows)

11. **Character Memory™ callbacks** — canon.json events fed to Gemini → running
    gags ("the samosa incident") compound loyalty.
12. **Emotion sticker variants** — each character gets 3 faces (normal/shook/
    rage); render picks per line sentiment.
13. **SFX design kit** — CC0 whoosh/pop/dun-dun-dun stingers on speaker
    switches + cliffhangers (audio identity).
14. **Bg-story energy matching** — chill story → ASMR/restock bg; chaos story →
    parkour bg. Auto via Gemini energy tag (playbook §3 logic applied to bg).
15. **Thumbnail frame law** — long-form gets custom PIL thumbnails (playbook §2).
16. **"Meet the cast" intro wave** — first 10 episodes each spotlight one
    character → audience attachment before the arcs start.
17. **Comment-reply drafting** — after 1h, engine drafts replies (owner sends
    from phone app = human touch, constitution-compliant).
18. **Weekly best-of long** — every 2 days per playbook; compilations with
    narrator intros = long-form watch-hours for YPP.

## B-tier (growth phase)

19. **Choose-the-ending polls** — Community polls decide Part-2 outcomes →
    invested viewers = return viewers.
20. **Pinned-comment quizzes** — "what would YOU have done?" comment bait.
21. **Season finale events** — character birthdays, exam results day, Eid/
    Puja/Christmas specials (calendar-aware).
22. **4th-wall subscriber milestones** — characters "notice" the sub count.
23. **Spin-off BN channel** if Bangla APV beats EN (own vessel per §B).
24. **Dubs of winners** — best EN episodes re-voiced BN/HI (and vice versa).

## C-tier (moonshots)

25. **Mouth-flap animation** on stickers (FFmpeg scale/rotate keyframes timed to
    word boundaries).
26. **Viewer story submissions** — "comment your craziest family story" →
    canonized episodes (credit in description) = infinite free ideation.
27. **Per-scene AI music** instead of stock bed.
28. **Character shorts SPAWN** — 1-character deep cuts (e.g. "Nani roasts 2026").

## Engine housekeeping (boring but vital)

- Render-ahead vault (≥1 video ready before every slot — golden rule §0)
- Weekly maint workflow: prune artifacts, streak report issue, cadence audit
- Repo secret vaulting via API (sealed, never in files — see SETUP_GUIDE)
- Dual Gemini keys + model fallback chain (playbook §6)
- All uploads unlisted-first → verify with yt-dlp probe → flip public (§7)
