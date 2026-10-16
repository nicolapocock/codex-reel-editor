import importlib.util, json, os, tempfile, threading, urllib.request, urllib.error
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
    assert b'Thumbnail studio' in get('/').read()
    assert b'Download portrait PNG' in get('/thumbnail').read()
    assert json.load(get('/api/thumbnail'))['sources'] == []
    with tempfile.TemporaryDirectory() as home:  # brand comes from REELS_HOME, not the reel folder
        Path(home,'brand.json').write_text('{"colors":{"main":"#123456"}}');os.environ['REELS_HOME']=home
        assert json.load(get('/api/thumbnail'))['color']=='#123456'
    cover = dict(source='raw.mp4', time=1.2, title='my ai reel editor', style='shadow', color='#ed84b0', position=280, size=108, font='system-ui', guides=True)
    req=urllib.request.Request(url+'/api/thumbnail',data=json.dumps(cover).encode(),method='PUT',headers={'Origin':url,'Content-Type':'application/json'})
    assert json.load(urllib.request.urlopen(req))['saved']
    assert json.load(get('/api/thumbnail'))['settings']==cover
    for override in ({'time':float('nan')},{'source':'../../secret'},{'title':'x'*161},{'size':999}):
        req=urllib.request.Request(url+'/api/thumbnail',data=json.dumps({**cover,**override}).encode(),method='PUT',headers={'Origin':url})
        try: urllib.request.urlopen(req);raise AssertionError('invalid cover accepted')
        except urllib.error.HTTPError as e: assert e.code==400
    assert json.load(get('/api/thumbnail'))['settings']==cover
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
