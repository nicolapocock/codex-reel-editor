"""Verify saved word decisions reach the renderer's EDL and captions."""
import json
import subprocess
import tempfile
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'skills/reel-editor/scripts/review_sync.py'
with tempfile.TemporaryDirectory() as folder:
    reel = Path(folder)
    (reel / 'raw.mp4').touch()
    data = {'title':'Test', 'srcDur':3, 'speed':1, 'pacing':{'air':0.06,'pause_min':0.25},
            'words':[{'text':'Hello','s':0.1,'e':0.7}, {'text':'um','s':0.8,'e':1.1,'filler':True},
                     {'text':'world','s':1.2,'e':1.9}, {'text':'again','s':2,'e':2.7}],
            'proposedCut':[], 'keepPauses':[], 'board':[],
            'captions':[{'w':[0],'acc':[]},{'w':[2,3],'acc':[2]}]}
    (reel/'review_reel.json').write_text(json.dumps(data))
    (reel/'review_decisions.json').write_text(json.dumps({'cut':[3]}))
    subprocess.run(['python3',str(script),'import',str(reel),str(reel/'review_decisions.json')],check=True)
    edl=json.loads((reel/'edl.json').read_text());edit=json.loads((reel/'edit.json').read_text())
    assert edl['source']=='raw.mp4'
    assert len(edl['keep'])==2, edl
    assert edl['keep'][0][1] < 0.8 and edl['keep'][1][0] > 1.1
    words=[w['text'] for c in edit['captions'] for w in c['words']]
    assert words==['Hello','world'],words
    assert edit['captions'][1]['words'][0]['accent']
    assert edit['hash']
print('PASS: cuts, filler removal and accent captions survive review import')
