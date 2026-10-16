#!/usr/bin/env python3
"""Render an immutable snapshot of review decisions, preserving the previous preview on failure."""
import copy
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

S = Path(__file__).resolve().parent

def atomic_json(path, value):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(value,indent=2));os.replace(temp,path)

def publish_cover_assets(reel, job):
    """Expose the successful build to cover creation without re-rendering footage."""
    for name in ('master.mp4', 'final.mp4'):
        temp = reel / (name + '.tmp')
        shutil.copy2(job / name, temp)
        os.replace(temp, reel / name)
    fonts = reel / 'review-assets' / 'cover-fonts'
    fonts.mkdir(parents=True, exist_ok=True)
    for source in (job / 'proj' / 'fonts').iterdir():
        if source.is_file():
            temp = fonts / (source.name + '.tmp')
            shutil.copy2(source, temp)
            os.replace(temp, fonts / source.name)

class PreviewBuilder:
    def __init__(self,reel):
        self.reel=reel.resolve();self.lock=threading.Lock();self.status={'state':'idle','message':'Ready to build'}
    def start(self, decisions):
        with self.lock:
            if self.status['state'] in ('queued','running'): raise ValueError('A preview is already building. Wait for it to finish.')
            if any((v or {}).get('state')=='c' for v in decisions.get('board',{}).values()) or any(str(v).strip() for v in decisions.get('notes',{}).values()) or decisions.get('revisions') or decisions.get('brandRequest','').strip():
                raise ValueError('Your written change requests need Codex to review them before building. Return to chat and ask it to apply your saved notes.')
            self.status={'state':'queued','message':'Preparing your approved edit'}
            threading.Thread(target=self.build,args=(copy.deepcopy(decisions),),daemon=True).start()
            return dict(self.status)
    def build(self, decisions):
        reel=self.reel;build_id=uuid.uuid4().hex[:12];job=reel/'.builds'/build_id
        try:
            job.mkdir(parents=True)
            config=json.loads((reel/'review_config.json').read_text())
            brand_home=Path(config['brandHome'])
            brand=json.loads((brand_home/'brand.json').read_text())
            # Fonts and optional music remain anchored to their original locations.
            for font in brand.get('fonts',{}).values():
                if font.get('file'): font['file']=str(Path(font['file']).expanduser().resolve())
            atomic_json(job/'brand.json',brand)
            for path in reel.iterdir():
                if path.name in ('review_reel.json',): shutil.copy2(path,job/path.name)
                elif path.name.startswith('raw.') or path.name in ('voice.wav','shots','review-assets'):
                    (job/path.name).symlink_to(path)
            atomic_json(job/'decisions.json',decisions)
            env={**os.environ,'REELS_HOME':str(job),'REEL_PREVIEW':'1'}
            log_path=reel/'review_build.log'
            with log_path.open('w') as log:
                def run(message,args):
                    with self.lock: self.status={'state':'running','message':message,'id':build_id}
                    log.write(message+'\n');log.flush()
                    subprocess.run([str(a) for a in args],env=env,stdout=log,stderr=log,check=True,timeout=1800)
                run('Applying cuts and captions',[sys.executable,S/'review_sync.py','import',job,job/'decisions.json'])
                run('Cutting footage and preparing audio',[sys.executable,S/'cut.py',job])
                run('Rendering your preview — this can take a few minutes',['bash',S/'render.sh',job])
                run('Checking size, duration and audio',[sys.executable,S/'qa.py',job])
            edit=json.loads((job/'edit.json').read_text())
            out=reel/'review-assets'/f'preview-{build_id}.mp4';out.parent.mkdir(exist_ok=True)
            shutil.copy2(job/'final.mp4',out)
            dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(out)],text=True))
            publish_cover_assets(reel, job)
            atomic_json(reel/'review_build.json',{'url':'/media/review-assets/'+out.name,'hash':edit['hash'],
                'at':datetime.now(timezone.utc).isoformat(),'cutDur':dur,'id':build_id})
            # Keep the matching decisions/edit available without changing the live review.
            atomic_json(reel/'last_built_decisions.json',decisions)
            for name in ('edl.json','edit.json'): shutil.copy2(job/name,reel/name)
            with self.lock: self.status={'state':'complete','message':'Your preview is ready','id':build_id}
        except Exception as e:
            with self.lock: self.status={'state':'error','message':f'Preview failed: {e}. Your last preview is safe. Ask Codex to inspect review_build.log.','id':build_id}
