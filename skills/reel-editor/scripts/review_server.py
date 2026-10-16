#!/usr/bin/env python3
"""Serve a single reel review on localhost. No dependencies or cloud uploads."""
import argparse
import json
import mimetypes
import os
import re
import threading
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from build_preview import PreviewBuilder
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

UI = Path(__file__).resolve().parents[1] / 'review'
DOCS = {'reel/current': 'review_reel.json', 'review/current': 'review_decisions.json',
        'builds/latest': 'review_build.json'}

def make_handler(reel, enable_builds=False):
    reel = reel.resolve()
    write_lock = threading.Lock()
    builder = PreviewBuilder(reel) if enable_builds else None
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == '/api/thumbnail':
                brand_path = reel / 'brand.json'
                brand = json.loads(brand_path.read_text()) if brand_path.exists() else {}
                sources = [name for name in ('master-before-bg.mp4', 'master.mp4', 'raw1080.mp4', 'raw.mp4', 'final.mp4') if (reel / name).is_file()]
                fonts = []
                for font in brand.get('fonts', {}).values():
                    name = Path(font.get('file', '')).name
                    local = reel / 'proj' / 'fonts' / name
                    if local.is_file() and local.resolve().is_relative_to(reel):
                        fonts.append({'family': font.get('family', name), 'url': '/media/proj/fonts/' + name, 'weight': font.get('weight', 400)})
                self.send_json({'sources': sources, 'fonts': fonts, 'color': brand.get('colors', {}).get('main', '#ED84B0'), 'name': reel.name, 'settings': json.loads((reel / 'thumbnail_settings.json').read_text()) if (reel / 'thumbnail_settings.json').exists() else {}}); return
            if path == '/api/status':
                self.send_json({**(builder.status if builder else {'state':'disabled','message':'Builds are disabled'}), 'enabled': bool(builder)}); return
            if path.startswith('/api/'):
                name = DOCS.get(path[5:])
                if not name:
                    self.send_error(404); return
                file = reel / name
                self.send_json(json.loads(file.read_text()) if file.exists() else None)
                return
            if path in ('/', '/reel-review.html'):
                file = UI / 'reel-review.html'
            elif path == '/setup':
                file = UI / 'setup.html'
            elif path == '/thumbnail':
                file = UI / 'thumbnail.html'
            elif path == '/core.js':
                file = UI / 'core.js'
            elif path.startswith('/media/'):
                file = (reel / path[7:]).resolve()
                if not file.is_relative_to(reel):
                    self.send_error(403); return
            else:
                self.send_error(404); return
            if not file.is_file():
                self.send_error(404); return
            size = file.stat().st_size
            start, end = 0, size - 1
            header = self.headers.get('Range')
            if header:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
                if not match or not any(match.groups()):
                    self.send_error(416); return
                a, b = match.groups()
                if a:
                    start = int(a); end = min(int(b), end) if b else end
                else:
                    start = max(0, size - int(b))
                if start > end or start >= size:
                    self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return
            self.send_response(206 if header else 200)
            self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Cache-Control', 'no-store')
            if header: self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with file.open('rb') as stream:
                stream.seek(start); remaining = end - start + 1
                try:
                    while remaining:
                        chunk = stream.read(min(65536, remaining))
                        if not chunk: break
                        self.wfile.write(chunk); remaining -= len(chunk)
                except (BrokenPipeError, ConnectionResetError): pass

        def do_POST(self):
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected[7:] or self.headers.get('Origin') not in (None, expected) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.send_error(403); return
            if self.path != '/api/build' or builder is None:
                self.send_error(403); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2_000_000: raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict): raise ValueError('Expected decisions object')
                self.validate_decisions(data)
                self.send_json(builder.start(data))
            except (ValueError, TypeError) as error:
                self.send_json({'error':str(error)}, 400)

        def validate_decisions(self, data):
            if not isinstance(data, dict): raise ValueError('Expected decisions object')
            for key in ('cut','restoredFillers','restoredPauses','trimmedPauses'):
                if data.get(key) is not None and (not isinstance(data[key],list) or any(type(i) is not int or i < 0 for i in data[key])):
                    raise ValueError('Invalid word selection')
            for key in ('board','notes','sfxOff','captionStyle'):
                if key in data and not isinstance(data[key],dict): raise ValueError('Invalid '+key)
            if data.get('audioMode','cleaned') not in ('cleaned','original'): raise ValueError('Invalid audio mode')
            style=data.get('captionStyle',{})
            for key,lo,hi in [('capY',200,1550),('capSize',32,150)]:
                if key in style and (type(style[key]) not in (int,float) or not lo <= style[key] <= hi):
                    raise ValueError('Caption setting outside safe range')

        def do_PUT(self):
            # Only the same-origin review UI may write. Reject browser cross-site requests.
            origin = self.headers.get('Origin')
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if origin and origin != expected:
                self.send_error(403); return
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.send_error(403); return
            if self.headers.get('Host') != expected[7:]:
                self.send_error(403); return
            if self.path not in ('/api/review/current', '/api/thumbnail'):
                self.send_error(403); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0 or length > 2_000_000: raise ValueError('Invalid size')
                data = json.loads(self.rfile.read(length))
                if self.path == '/api/thumbnail':
                    if not isinstance(data, dict): raise ValueError('Expected settings')
                    allowed = {'source','time','title','style','color','position','size','font','guides'}
                    if set(data) - allowed: raise ValueError('Unknown setting')
                    for key in ('source','title','style','color','font'):
                        if not isinstance(data.get(key), str): raise ValueError('Invalid text setting')
                    if len(data['title']) > 160: raise ValueError('Title too long')
                    if data['source'] not in ('master-before-bg.mp4','master.mp4','raw1080.mp4','raw.mp4','final.mp4'): raise ValueError('Invalid source')
                    if data['style'] not in ('shadow','panel','dark'): raise ValueError('Invalid style')
                    if not re.fullmatch(r'#[0-9a-fA-F]{6}', data['color']): raise ValueError('Invalid colour')
                    for key, lo, hi in [('time',0,86400),('position',120,1500),('size',48,150)]:
                        if type(data.get(key)) not in (int,float) or not lo <= data[key] <= hi: raise ValueError('Invalid range')
                    if type(data.get('guides')) is not bool: raise ValueError('Invalid guides')
                else:
                    self.validate_decisions(data)
            except (ValueError, json.JSONDecodeError):
                self.send_error(400); return
            with write_lock:
                destination = reel / ('thumbnail_settings.json' if self.path == '/api/thumbnail' else DOCS['review/current'])
                tmp = destination.with_suffix('.json.tmp')
                tmp.write_text(json.dumps(data, indent=2))
                os.replace(tmp, destination)
            self.send_json({'saved': True})

        def send_json(self, value, status=200):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reel', type=Path)
    parser.add_argument('--port', type=int, default=0, help='0 chooses a free port')
    parser.add_argument('--enable-builds', action='store_true', help='Allow the Build preview button to render locally')
    args = parser.parse_args()
    reel = args.reel.resolve()
    if not (reel / 'review_reel.json').is_file():
        parser.error('Run review_sync.py export first; review_reel.json is missing')
    with ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(reel, args.enable_builds)) as server:
        print(f'Reel Review: http://127.0.0.1:{server.server_port}/', flush=True)
        print(f'Decisions: {reel / "review_decisions.json"}', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass

if __name__ == '__main__': main()
