import json
import mimetypes
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from engine import Engine

ROOT=Path(__file__).parent/'static'
DATA=Path(os.environ.get('DATA_DIR','./data')); DATA.mkdir(parents=True,exist_ok=True)
engine=Engine(str(DATA/'simulation.sqlite3'))

class Handler(BaseHTTPRequestHandler):
    def json_response(self, data, status=200):
        payload=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/health': return self.json_response({'ok':True})
        if path=='/api/state': return self.json_response(engine.snapshot())
        if path=='/api/config':
            s=engine.snapshot()
            return self.json_response({'version':1,'stations':s['stations'],'vehicles':[{k:v[k] for k in ('id','callsign','type','station','start','end','staffed','source')} for v in s['vehicles']]})
        file=(ROOT/('index.html' if path=='/' else path.lstrip('/'))).resolve()
        if not file.is_relative_to(ROOT.resolve()) or not file.is_file(): return self.json_response({'error':'Nicht gefunden'},404)
        payload=file.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(file)[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(payload))); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(payload)

    def do_POST(self):
        # Browser requests must come from the same origin; CLI tools may omit Origin.
        if self.headers.get('Origin') and urlparse(self.headers['Origin']).netloc!=self.headers.get('Host'):
            return self.json_response({'error':'Fremde Herkunft nicht erlaubt.'},403)
        path=urlparse(self.path).path
        if not path.startswith('/api/'): return self.json_response({'error':'Nicht gefunden'},404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1_000_000: return self.json_response({'error':'Ungültige Anfragegröße.'},413)
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('JSON-Objekt erforderlich.')
            result=engine.command(path.removeprefix('/api/'),data)
            self.json_response(result)
        except (ValueError,KeyError,TypeError,StopIteration) as e:
            self.json_response({'error':str(e) or 'Ungültige Eingabe.'},400)

    def log_message(self,format,*args): pass


def run_clock():
    last=time.monotonic()
    while True:
        time.sleep(1); now=time.monotonic()
        engine.tick(min(now-last,5)); last=now

if __name__=='__main__':
    threading.Thread(target=run_clock,daemon=True).start()
    print('NÖ Dispo läuft auf Port 8080',flush=True)
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
