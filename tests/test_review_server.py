import importlib.util, json, tempfile, threading, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
p=Path(__file__).resolve().parents[1] / 'skills/reel-editor/scripts/review_server.py'
spec=importlib.util.spec_from_file_location('server',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
    r=Path(d);(r/'review_reel.json').write_text('{"title":"test"}');(r/'clip.mp4').write_bytes(b'0123456789')
    server=ThreadingHTTPServer(('127.0.0.1',0),m.make_handler(r)); threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
    def get(path,headers={}): return urllib.request.urlopen(urllib.request.Request(url+path,headers=headers))
    assert json.load(get('/api/reel/current'))['title']=='test'
    assert b'localDB' in get('/').read()
    assert get('/media/clip.mp4',{'Range':'bytes=2-5'}).read()==b'2345'
    assert get('/media/clip.mp4',{'Range':'bytes=-3'}).read()==b'789'
    data={'cut':[1],'buildRequest':{'hash':'a'},'revisions':[{'t':1,'text':'fix'}]}
    req=urllib.request.Request(url+'/api/review/current',data=json.dumps(data).encode(),method='PUT',headers={'Origin':url,'Content-Type':'application/json'})
    assert json.load(urllib.request.urlopen(req))['saved']
    assert json.load(get('/api/review/current'))==data
    for path in ['/media/../outside','/api/unknown']:
        try: get(path);raise AssertionError(path)
        except urllib.error.HTTPError as e: assert e.code in (403,404)
    req=urllib.request.Request(url+'/api/review/current',data=b'{}',method='PUT',headers={'Origin':'https://example.com'})
    try: urllib.request.urlopen(req);raise AssertionError('cross-origin')
    except urllib.error.HTTPError as e: assert e.code==403
    server.shutdown()
print('PASS: review page, persisted decisions, video ranges, path boundary, cross-origin rejection')
