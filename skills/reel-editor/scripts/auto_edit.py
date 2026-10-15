#!/usr/bin/env python3
"""Draft edit.json from the cut master's transcript: captions chunked in the brand's caption mode and punch-ins on a
steady rhythm. Codex then only marks accent words and adds 3-6 cards - no design work.
Usage: python3 auto_edit.py <reel-folder>     (needs <reel-folder>/master_transcript.json; see SKILL.md step 5)"""
import json, os, re, sys
from pathlib import Path

reel = Path(sys.argv[1]).expanduser()
home = Path(os.environ.get("REELS_HOME", "~/reels")).expanduser()
brand = json.load(open(home / "brand.json"))
mode = brand.get("captions", {}).get("mode", "phrase")          # "word" = one word at a time, "phrase" = 2-4 words
words = [w for w in json.load(open(reel / "master_transcript.json")) if w["text"].strip()]

def clean(t): return re.sub(r"[^\w'’$%&+#@-]", "", t)

captions, cur = [], []
def flush():
    if cur:
        captions.append({"start": round(cur[0]["start"], 2), "end": round(cur[-1]["end"], 2),
                         "words": [{"text": clean(w["text"]), "t": round(w["start"], 2), "accent": False} for w in cur]})
        cur.clear()
for i, w in enumerate(words):
    cur.append(w)
    gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
    if mode == "word" or len(cur) >= 3 or re.search(r"[.,!?;:]$", w["text"]) or gap > 0.35:
        flush()
flush()
for a, b in zip(captions, captions[1:]):                         # hold each caption until the next one starts
    a["end"] = round(max(a["end"], min(b["start"], a["end"] + 0.6)), 2)

# punch-ins: on every sentence start, plus at least every ~2.2 s
punch, last = [], -9.0
for i, w in enumerate(words):
    new_sentence = i == 0 or re.search(r"[.!?]$", words[i - 1]["text"])
    if new_sentence and w["start"] - last > 1.2 or w["start"] - last > 2.2:
        punch.append(round(w["start"], 2)); last = w["start"]

json.dump({"captions": captions, "punch": punch, "cards": [], "captionStyle": {"fixedPosition": True}}, open(reel / "edit.json", "w"), indent=1)
print(f"edit.json: {len(captions)} captions ({mode} mode), {len(punch)} punch-ins, 0 cards - now mark accents + add cards")
