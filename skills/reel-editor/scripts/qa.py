#!/usr/bin/env python3
"""QA gate for a finished reel. Checks size, length, loudness, and (if expected.txt exists) that no words were lost.
Usage: python3 qa.py <reel-folder> [video]     default video: final.mp4. Exit code 1 if anything fails."""
import difflib, json, os, re, subprocess, sys
from pathlib import Path

reel = Path(sys.argv[1]).expanduser()
video = reel / (sys.argv[2] if len(sys.argv) > 2 else "final.mp4")
home = Path(os.environ.get("REELS_HOME", "~/reels")).expanduser()
brand = json.load(open(home / "brand.json"))
fails = []

def probe(entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
                          "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)

info = probe("stream=width,height:format=duration")
w, h = info["streams"][0]["width"], info["streams"][0]["height"]
dur = float(info["format"]["duration"])
want = [1080, 1920] if os.environ.get("REEL_PREVIEW") else brand.get("resolution", [1080, 1920])
print(f"size      {w}x{h}  (want {want[0]}x{want[1]})")
if [w, h] != list(want): fails.append("size")
print(f"length    {dur:.1f}s  (max {brand.get('max_seconds', 60)}s)")
if dur > brand.get("max_seconds", 60): fails.append("length")

ebu = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)[-1])
print(f"loudness  {lufs:.1f} LUFS  (want -15 to -12.5)")
if not -15 <= lufs <= -12.5: fails.append("loudness")

exp = reel / "expected.txt"
if exp.exists():
    tok = lambda s: re.sub(r"[^a-z0-9' ]", " ", re.sub(r"(?<=\d),(?=\d)", "", s.lower())).split()   # "5,000" == "5000"
    r = subprocess.run(["npx", "-y", "hyperframes", "transcribe", str(video), "-d", str(reel / "qa_transcript"),
                        "--json", "--model", "small.en"], capture_output=True, text=True)
    if r.returncode: sys.exit(f"QA could not transcribe the video:\n{r.stderr.strip()[-1500:]}")
    heard = [t for wd in json.load(open(reel / "qa_transcript/transcript.json")) for t in tok(wd["text"])]
    expected = tok(exp.read_text())
    # brand.json "vocab": names the transcriber misspells ("Claude" -> "Clord"). A same-length swap of only vocab words
    # counts as heard; a clipped word still shows up as a deletion.
    vocab = {t for v in brand.get("vocab", []) for t in tok(v)}
    in_vocab = lambda t: t in vocab or re.sub(r"'s$", "", t) in vocab
    ops = difflib.SequenceMatcher(None, expected, heard, autojunk=False).get_opcodes()
    ok = lambda op, i1, i2, j1, j2: op == "replace" and i2 - i1 == j2 - j1 and all(in_vocab(t) for t in expected[i1:i2])
    same = sum(i2 - i1 for op, i1, i2, j1, j2 in ops if op == "equal" or ok(op, i1, i2, j1, j2))
    ratio = 2 * same / max(1, len(expected) + len(heard))
    missing = [expected[i1:i2] for op, i1, i2, j1, j2 in ops if op in ("delete", "replace") and not ok(op, i1, i2, j1, j2)]
    print(f"words     {ratio:.0%} match" + (f"; check: {missing[:6]}" if missing else ""))
    # one clipped word barely moves the ratio, and the first and last words are where cuts clip most
    lost = {i for op, i1, i2, j1, j2 in ops if op in ("delete", "replace") and not ok(op, i1, i2, j1, j2) for i in range(i1, i2)}
    edge = sorted(lost & {0, len(expected) - 1})
    if edge: print(f"          first/last word missing: {[expected[i] for i in edge]} (clipped at the start or end?)")
    if ratio < 0.95 or edge: fails.append("words")
else:
    print("words     skipped (write the approved script to expected.txt to check for clipped words)")

print("PASS" if not fails else f"FAIL: {', '.join(fails)}")
sys.exit(1 if fails else 0)
