import json
import mimetypes
import os
from pathlib import Path
import re
import threading
import time
from collections import defaultdict,deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from sessions import Sessions
from catalog import CENTRES,ZONES,RULES,TRANSPORT_RULES
from locations import ADDRESSES
from aao import SOURCE,code_rule

ROOT=Path(__file__).parent/'static'
DATA=Path(os.environ.get('DATA_DIR','./data')); DATA.mkdir(parents=True,exist_ok=True)
sessions=Sessions(str(DATA/'simulation.sqlite3'))
limits=defaultdict(deque);limit_lock=threading.Lock()
live_changes=threading.Condition()

def notify_live():
    with live_changes:live_changes.notify_all()

class Handler(BaseHTTPRequestHandler):
    def respond(self,payload,content_type,status=200):
        try:
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError):pass
    def json_response(self,data,status=200):self.respond(json.dumps(data,ensure_ascii=False).encode(),'application/json; charset=utf-8',status)
    def member(self):return sessions.member(self.headers.get('Authorization','').removeprefix('Bearer '))
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/live':
            try:member=self.member()
            except PermissionError as e:return self.json_response({'error':str(e)},401)
            self.send_response(200);self.send_header('Content-Type','text/event-stream; charset=utf-8');self.send_header('Cache-Control','no-cache, no-transform');self.send_header('X-Accel-Buffering','no');self.send_header('Connection','close');self.end_headers()
            last=None;heartbeat=time.monotonic()
            try:
                while True:
                    if not sessions.stream_touch(member):return
                    state=sessions.snapshot(member);sync=state.pop('sync_time');body=json.dumps(state,ensure_ascii=False,separators=(',',':'))
                    if body!=last:
                        state['sync_time']=sync
                        self.wfile.write(('event: state\ndata: '+json.dumps(state,ensure_ascii=False,separators=(',',':'))+'\n\n').encode());self.wfile.flush();last=body;heartbeat=time.monotonic()
                    elif time.monotonic()-heartbeat>5:
                        self.wfile.write(b': heartbeat\n\n');self.wfile.flush();heartbeat=time.monotonic()
                    with live_changes:live_changes.wait(timeout=1)
            except (BrokenPipeError,ConnectionResetError,PermissionError):return
        if path=='/api/addresses':return self.json_response({'addresses':ADDRESSES,'source':'© OpenStreetMap contributors · ODbL 1.0'})
        if path=='/api/codes':return self.json_response({'date':SOURCE['date'],'rules':[code_rule(r['code']) for r in SOURCE['entries']]+TRANSPORT_RULES})
        if path=='/api/catalog':return self.json_response({'centres':CENTRES,'zones':ZONES,'rules':RULES})
        if path=='/api/health':return self.json_response({'ok':True,'version':'0.10'})
        if path in ('/api/state','/api/config'):
            try:
                s=sessions.snapshot(self.member())
                if path=='/api/config':s={'version':2,'stations':s['stations'],'vehicles':[{k:v.get(k) for k in ('id','callsign','type','station','start','end','staffed','source','graphic','nfs','turnout','organization','rtwc_capable','rtwc_fixed','daylight','duty_managed','home_lat','home_lon','home_address')} for v in s['vehicles']]}
                return self.json_response(s)
            except PermissionError as e:return self.json_response({'error':str(e)},401)
        if path.startswith('/media/'):
            id=path.removeprefix('/media/').removesuffix('.png')
            if re.fullmatch(r'[a-f0-9]{32}',id):
                content=sessions.media(id)
                if content:return self.respond(content,'image/png')
            return self.json_response({'error':'Bild nicht gefunden'},404)
        file=(ROOT/('index.html' if path=='/' else path.lstrip('/'))).resolve()
        if not file.is_relative_to(ROOT.resolve()) or not file.is_file():return self.json_response({'error':'Nicht gefunden'},404)
        return self.respond(file.read_bytes(),mimetypes.guess_type(file)[0] or 'application/octet-stream')
    def do_POST(self):
        if self.headers.get('Origin') and urlparse(self.headers['Origin']).netloc!=self.headers.get('Host'):return self.json_response({'error':'Fremde Herkunft nicht erlaubt.'},403)
        path=urlparse(self.path).path
        if not path.startswith('/api/'):return self.json_response({'error':'Nicht gefunden'},404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1_000_000:return self.json_response({'error':'Ungültige Anfragegröße.'},413)
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('JSON-Objekt erforderlich.')
            action=path.removeprefix('/api/')
            if action in ('session/create','session/join'):
                with limit_lock:
                    # All callers behind one tunnel may share an address; generous bound.
                    key=self.client_address[0];now=time.monotonic();window=limits[key]
                    while window and now-window[0]>60:window.popleft()
                    if len(window)>=30:return self.json_response({'error':'Zu viele Beitrittsversuche. Bitte eine Minute warten.'},429)
                    window.append(now)
                credential=sessions.create(data) if action=='session/create' else sessions.join(data)
                member=sessions.member(credential['token']);return self.json_response({**credential,'state':sessions.snapshot(member)})
            member=self.member();result=sessions.command(member,action,data);notify_live();self.json_response(result)
        except PermissionError as e:self.json_response({'error':str(e)},403)
        except (ValueError,KeyError,TypeError,StopIteration) as e:self.json_response({'error':str(e) or 'Ungültige Eingabe.'},400)
    def log_message(self,format,*args):pass

def run_clock():
    last=time.monotonic()
    while True:
        time.sleep(1);now=time.monotonic();sessions.tick(min(now-last,5));last=now;notify_live()

if __name__=='__main__':
    threading.Thread(target=run_clock,daemon=True).start()
    print('NÖ Dispo v0.10 läuft auf Port 8080',flush=True)
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
