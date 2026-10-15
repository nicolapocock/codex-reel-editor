#!/usr/bin/env python3
"""Prepare a local review with footage, transcript, brand, proposal and playable assets."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

S = Path(__file__).resolve().parent

def run(*args):
    subprocess.run([str(a) for a in args], check=True)

def prepare(reel, brand_home):
    reel = reel.resolve(); brand_home = brand_home.resolve()
    os.environ['REELS_HOME'] = str(brand_home)
    brand = json.loads((brand_home / 'brand.json').read_text())
    raw = next((p for p in sorted(reel.glob('raw.*')) if p.suffix.lower() in ('.mp4','.mov','.m4v')), None)
    if not raw: raise ValueError('Copy your recording into the reel folder as raw.mp4 or raw.mov first.')
    for name in ('transcript.json', 'proposal.json'):
        if not (reel / name).exists(): raise ValueError(f'Missing {name}. Ask Codex to prepare the transcript and edit proposal.')
    assets = reel / 'review-assets'; assets.mkdir(exist_ok=True)
    if not (reel / 'voice.wav').exists():
        run('bash', S / 'clean_audio.sh', raw, reel / 'voice.wav', '--no-denoise')
    run(sys.executable, S / 'review_sync.py', 'export', reel, reel / 'proposal.json', reel / 'review-export')
    run('ffmpeg','-v','error','-y','-i',raw,'-vf','scale=540:960:force_original_aspect_ratio=increase,crop=540:960',
        '-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-movflags','+faststart',assets/'original.mp4')
    run('ffmpeg','-v','error','-y','-i',assets/'original.mp4','-i',reel/'voice.wav','-map','0:v:0','-map','1:a:0',
        '-c:v','copy','-c:a','aac','-shortest','-movflags','+faststart',assets/'source.mp4')
    for name, source in [('audio-original',raw),('audio-cleaned',reel/'voice.wav')]:
        run('ffmpeg','-v','error','-y','-i',source,'-t','10','-vn','-c:a','aac',assets/(name+'.m4a'))
    data=json.loads((reel/'review_reel.json').read_text())
    data.update(srcUrl='/media/review-assets/source.mp4',srcOriginalUrl='/media/review-assets/original.mp4',
        assets={'audioOriginal':'/media/review-assets/audio-original.m4a','audioCleaned':'/media/review-assets/audio-cleaned.m4a'},fonts={})
    for role in ('body','accent'):
        font=Path(brand.get('fonts',{}).get(role,{}).get('file','')).expanduser()
        if font.is_file():
            dst=assets/(role+font.suffix);shutil.copy2(font,dst);data['fonts'][role]='/media/review-assets/'+quote(dst.name)
    for i, card in enumerate(data['board']):
        dst=assets/f'thumb-{i}.jpg'
        run('ffmpeg','-v','error','-y','-ss',data['words'][card['w0']]['s'],'-i',raw,'-frames:v','1','-vf','scale=180:320',dst)
        card['thumbUrl']='/media/review-assets/'+dst.name
    (reel/'review_reel.json').write_text(json.dumps(data,indent=2))
    (reel/'review_config.json').write_text(json.dumps({'brandHome':str(brand_home)},indent=2))
    print('Ready. Start review_server.py with this reel folder and --enable-builds to review and render.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reel',type=Path);p.add_argument('--brand-home',type=Path,required=True)
    a=p.parse_args();prepare(a.reel,a.brand_home)
