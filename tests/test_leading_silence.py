"""A clip that opens on silence must not lose its first words (Whisper pins them near 0 s)."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'skills/reel-editor/scripts/review_sync.py'
with tempfile.TemporaryDirectory() as folder:
    home = Path(folder); reel = home / 'reel'; reel.mkdir()
    (home / 'brand.json').write_text(json.dumps({'pacing': 'tight', 'colors': {'main': '#000000'}, 'captions': {}}))
    # 1.3 s of silence, then 1.7 s of "speech" (a tone)
    audio = 'aevalsrc=0.25*sin(2*PI*220*t)*gte(t\\,1.3):s=48000:d=3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', audio, str(reel / 'voice.wav')], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=s=64x64:d=3', '-i', str(reel / 'voice.wav'),
                    '-shortest', str(reel / 'raw.mp4')], check=True)
    # Whisper's timing for this kind of clip: "over five" placed over the silence
    (reel / 'transcript.json').write_text(json.dumps([{'text': 'Over', 'start': 0, 'end': 0.36},
        {'text': 'five', 'start': 0.36, 'end': 1.62}, {'text': 'people', 'start': 1.72, 'end': 2.6}]))
    proposal = reel / 'proposal.json'
    proposal.write_text(json.dumps({'title': 'T', 'proposedCut': [[0, 3]], 'cards': []}))
    env = {**os.environ, 'REELS_HOME': str(home)}
    subprocess.run(['python3', str(script), 'export', str(reel), str(proposal), str(reel / 'out')], check=True, env=env)
    subprocess.run(['python3', str(script), 'import', str(reel), str(reel / 'none.json')], check=True, env=env)
    keep = json.loads((reel / 'edl.json').read_text())['keep']
    words = json.loads((reel / 'review_reel.json').read_text())['words']
    assert words[0]['s'] >= 1.1, words          # moved onto the real speech
    assert keep[0][0] >= 1.0 and keep[0][0] <= 1.3, keep   # leading silence trimmed, opening word kept
    assert all(b - a > 0.3 for a, b in keep) and keep[-1][1] >= 2.6, keep
print('PASS: opening words survive a silent start')
