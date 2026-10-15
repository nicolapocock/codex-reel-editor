"""Exercise the actual renderer input, including custom sound handling."""
import json,os,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];script=root/'skills/reel-editor/scripts/build_reel.py'
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)
 subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=gray:s=108x192:d=1','-c:v','libx264',str(p/'master.mp4')],check=True)
 subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=500:duration=0.1',str(p/'click.wav')],check=True)
 brand={'colors':{'main':'#ED84B0','pop':'#FF7DB8'},'sfx':'lots','sfx_gain_db':0,'sfx_files':{'snap':'click.wav'},'captions':{'size':80,'y':1400}}
 edit={'captions':[{'start':0,'end':.9,'y':400,'words':[{'text':'hello','t':0}]}],'cards':[{'type':'title','text':'my ai / reel editor','single_line':True,'start':0,'end':.9,'quiet':False}]}
 (p/'brand.json').write_text(json.dumps(brand));(p/'edit.json').write_text(json.dumps(edit));env={**os.environ,'REELS_HOME':tmp}
 subprocess.run(['python3',str(script),tmp],env=env,check=True,capture_output=True)
 html=(p/'proj/index.html').read_text()
 assert 'my ai reel editor' in html and 'my ai / reel editor' not in html
 assert 'custom-1.wav' in html and (p/'proj/sfx/custom-1.wav').exists()
 assert 'top:1400px' in html and 'scale:0.86' not in html
 brand['sfx_files']['snap']='missing.wav';(p/'brand.json').write_text(json.dumps(brand))
 failed=subprocess.run(['python3',str(script),tmp],env=env,capture_output=True,text=True)
 assert failed.returncode!=0 and 'Sound file missing' in failed.stderr
print('PASS: real template build, fixed captions, single-line hook, custom audio and missing-file failure')
