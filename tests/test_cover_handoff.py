"""A successful review build must be usable by the cover studio."""
import sys, tempfile, json, threading, urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/reel-editor/scripts'))
from build_preview import publish_cover_assets
from review_server import make_handler
with tempfile.TemporaryDirectory() as tmp:
    reel=Path(tmp);job=reel/'.builds'/'test';fonts=job/'proj'/'fonts';fonts.mkdir(parents=True)
    (job/'master.mp4').write_bytes(b'new master');(job/'final.mp4').write_bytes(b'new export')
    (fonts/'brand.otf').write_bytes(b'font data');(reel/'final.mp4').write_bytes(b'old export')
    (reel/'brand.json').write_text(json.dumps({'fonts':{'head':{'file':'brand.otf','family':'Brand'}}}))
    publish_cover_assets(reel,job)
    assert (reel/'final.mp4').read_bytes()==b'new export'
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(reel));threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}'
    try:
        data=json.load(urllib.request.urlopen(url+'/api/thumbnail'))
        assert data['sources']==['master.mp4','final.mp4']
        assert data['fonts'][0]['family']=='Brand'
        assert urllib.request.urlopen(url+data['fonts'][0]['url']).read()==b'font data'
    finally:server.shutdown()
print('PASS: successful review build exposes master, export and brand fonts to thumbnail studio')
