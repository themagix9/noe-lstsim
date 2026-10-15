"""Persistent rooms, membership tokens and isolated simulation state."""
import base64
import datetime as dt
import copy
import hashlib
import secrets
import sqlite3
import struct
import threading
import time
from engine import Engine, GRAPHICS
from catalog import CENTRES, ZONES

class Sessions:
    def __init__(self,path):
        self.path=path; self.lock=threading.RLock(); self.engines={}
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('PRAGMA busy_timeout=5000'); self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS rooms (id TEXT PRIMARY KEY, code TEXT UNIQUE, title TEXT, created REAL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS members (id TEXT PRIMARY KEY, room_id TEXT, name TEXT, token_hash TEXT UNIQUE, host INTEGER, last_seen REAL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS graphics_files (id TEXT PRIMARY KEY, room_id TEXT, content BLOB)')
        if 'mode' not in {r[1] for r in self.db.execute('PRAGMA table_info(rooms)')}:
            self.db.execute("ALTER TABLE rooms ADD COLUMN mode TEXT NOT NULL DEFAULT 'multi'")
        if 'role' not in {r[1] for r in self.db.execute('PRAGMA table_info(members)')}:
            self.db.execute("ALTER TABLE members ADD COLUMN role TEXT NOT NULL DEFAULT 'both'")
        self.db.commit()
        # Run the legacy migration immediately, without discarding its saved state.
        self.engine('legacy')

    def engine(self,id):
        if id not in self.engines: self.engines[id]=Engine(self.path,id)
        return self.engines[id]

    def name(self,value):
        name=str(value or '').strip()
        if not 2<=len(name)<=30 or any(ord(c)<32 for c in name): raise ValueError('Spielername: 2–30 Zeichen.')
        return name

    def add_member(self,room,name,host=False,role='both'):
        if self.db.execute('SELECT count(*) FROM members WHERE room_id=?',(room,)).fetchone()[0]>=16: raise ValueError('Sitzung ist voll (maximal 16 Spieleridentitäten).')
        if self.db.execute('SELECT 1 FROM members WHERE room_id=? AND lower(name)=lower(?)',(room,name)).fetchone(): raise ValueError('Dieser Spielername ist bereits vergeben. Zum Fortsetzen den gespeicherten Zugang verwenden.')
        id=secrets.token_hex(16);token=secrets.token_urlsafe(32)
        self.db.execute('INSERT INTO members (id,room_id,name,token_hash,host,last_seen,role) VALUES (?,?,?,?,?,?,?)',(id,room,name,hashlib.sha256(token.encode()).hexdigest(),int(host),time.time(),role));self.db.commit()
        return {'token':token,'player':id}

    def create(self,data):
        with self.lock:
            name=self.name(data.get('name'));mode=data.get('mode','multi')
            if mode not in ('single','multi'):raise ValueError('Singleplayer oder Multiplayer wählen.')
            workflow=data.get('workflow','shared') if mode=='multi' else 'shared'
            if workflow not in ('shared','split'):raise ValueError('Gemeinsame oder getrennte Arbeitsweise wählen.')
            role=data.get('role','dispatcher') if workflow=='split' else 'both'
            if role not in (('calltaker','dispatcher') if workflow=='split' else ('both',)):raise ValueError('Calltaker oder Disponent wählen.')
            title=str(data.get('title') or ('Meine Leitstelle' if mode=='single' else 'Gemeinsame Disposition')).strip()[:60]
            if self.db.execute('SELECT count(*) FROM rooms').fetchone()[0]>=100: raise ValueError('Maximale Sitzungsanzahl erreicht.')
            centre=data.get('centre','Mödling');dispo=data.get('dispo','05');hour=int(data.get('hour',8))
            if centre not in CENTRES or dispo not in {z['id'] for z in ZONES} or not 0<=hour<=23:raise ValueError('Leitstellenstandort, Dispozone und Startzeit prüfen.')
            start_date=str(data.get('date') or dt.date.today().isoformat())
            try:date=dt.date.fromisoformat(start_date)
            except ValueError:raise ValueError('Simulationsdatum als JJJJ-MM-TT wählen.')
            if not 2020<=date.year<=2100:raise ValueError('Simulationsdatum zwischen 2020 und 2100 wählen.')
            id=secrets.token_hex(16)
            while True:
                code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
                if not self.db.execute('SELECT 1 FROM rooms WHERE code=?',(code,)).fetchone():break
            self.db.execute('INSERT INTO rooms (id,code,title,created,mode) VALUES (?,?,?,?,?)',(id,code,title,time.time(),mode));self.db.commit()
            e=self.engine(id)
            if data.get('adopt_legacy'):
                e.state=copy.deepcopy(self.engine('legacy').snapshot()); e.state['paused']=True
                for j in e.state['jobs']:j['owner']=None
                e.save()
            e.state['setup']={**e.state.get('setup',{}),'centre':centre,'dispo':dispo,'workflow':workflow,'blue_light_factor':e.state.get('setup',{}).get('blue_light_factor',.85)}
            if not data.get('adopt_legacy'):
                e.state['start_date']=start_date;e.state['clock']=hour*3600;e.state['next_transport']=hour*3600+(40 if workflow=='split' else 60);e.state['next_emergency']=hour*3600+(90 if workflow=='split' else 180)
                for v in e.state['vehicles']:v['status']=e.idle_status(v)
            e.save()
            credential=self.add_member(id,name,True,role);return credential

    def join(self,data):
        with self.lock:
            name=self.name(data.get('name'));code=str(data.get('code','')).strip().upper().replace(' ','').replace('-','')
            room=self.db.execute('SELECT id,mode FROM rooms WHERE code=?',(code,)).fetchone()
            if not room or room[1]=='single':raise ValueError('Multiplayer-Sitzungscode nicht gefunden.')
            role=data.get('role','dispatcher') if self.engine(room[0]).state['setup'].get('workflow')=='split' else 'both'
            if role not in (('calltaker','dispatcher') if self.engine(room[0]).state['setup'].get('workflow')=='split' else ('both',)):raise ValueError('Calltaker oder Disponent wählen.')
            return self.add_member(room[0],name,role=role)

    def member(self,token,touch=True):
        with self.lock:
            if not token or len(token)>200: raise PermissionError('Bitte einer Sitzung beitreten.')
            row=self.db.execute('SELECT id,room_id,name,host,last_seen,role FROM members WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not row:raise PermissionError('Sitzungszugang ungültig. Bitte erneut beitreten.')
            if touch:self.db.execute('UPDATE members SET last_seen=? WHERE id=?',(time.time(),row[0]));self.db.commit()
            return {'id':row[0],'room_id':row[1],'name':row[2],'host':bool(row[3]),'last_seen':row[4],'role':row[5]}

    def snapshot(self,member):
        with self.lock:
            room=self.db.execute('SELECT code,title,mode FROM rooms WHERE id=?',(member['room_id'],)).fetchone()
            roster=self.db.execute('SELECT id,name,host,last_seen,role FROM members WHERE room_id=?',(member['room_id'],)).fetchall()
            s=self.engine(member['room_id']).snapshot()
            s['sync_time']=time.time()
            s['session']={'code':room[0] if room[2]=='multi' else None,'mode':room[2],'title':room[1],'me':member['id'],'host':member['host'],'role':member.get('role','both'),'players':[{'id':r[0],'name':r[1],'host':bool(r[2]),'online':time.time()-r[3]<45,'role':r[4]} for r in roster]}
            return s

    def stream_touch(self,member):
        with self.lock:
            seen=self.db.execute('SELECT last_seen FROM members WHERE id=?',(member['id'],)).fetchone()
            if not seen or seen[0]==0:return False
            self.db.execute('UPDATE members SET last_seen=? WHERE id=?',(time.time(),member['id']));self.db.commit();return True

    def command(self,member,action,data):
        with self.lock:
            if action in ('vehicle','vehicle_graphic','station','delete_vehicle','import','reset','upload_graphic','rules','rtwc','travel_settings','event_settings','hospital') and not member['host']:raise PermissionError('Nur der Sitzungsleiter darf Stammdaten oder die Übung ändern.')
            engine=self.engine(member['room_id'])
            split=engine.state['setup'].get('workflow')=='split';role=member.get('role','both')
            if split:
                if action in ('accept','ask','call_question','call_finish','handoff') and role!='calltaker':raise PermissionError('Die Anrufabfrage übernimmt der Calltaker.')
                if action in ('dispatch','reserve','unreserve','bed_request','send_case','carrier','ask_cpr','radio','radio_retry','radio_generate','vehicle_status','vehicle_order','fuel_radio','fuel_request','resource_call','cancel_radio','signal_contact','signal_radio','support_request','support_cancel','agency_request','agency_release','agency_task','job_code') and role!='dispatcher':raise PermissionError('Die Einsatzdisposition übernimmt der Disponent.')
                if action in ('claim','edit_job','job_signal','dispatch','reserve','unreserve','support_request','support_cancel','job_additional','agency_request','agency_release','agency_task','job_code'):
                    job=engine.get('jobs',data.get('id') if action=='claim' else data.get('job'))
                    if job.get('call') and ((role=='dispatcher' and not job.get('handoff')) or (role=='calltaker' and job.get('handoff'))):raise PermissionError('Die Abfrage muss zuerst an die Disposition übergeben werden.' if role=='dispatcher' else 'Der Auftrag wurde bereits an die Disposition übergeben.')
            if action=='leave':
                mode=self.db.execute('SELECT mode FROM rooms WHERE id=?',(member['room_id'],)).fetchone()[0]
                if mode=='single':engine.command('control',{'paused':True})
                self.db.execute('UPDATE members SET last_seen=0 WHERE id=?',(member['id'],));self.db.commit();return {'left':True}
            if action=='claim':
                job=engine.get('jobs',data['id']);owner=job.get('owner')
                if job['status']=='done':raise ValueError('Einsatz bereits abgeschlossen.')
                if owner and owner!=member['id']:
                    seen=self.db.execute('SELECT last_seen FROM members WHERE id=? AND room_id=?',(owner,member['room_id'])).fetchone()
                    if seen and time.time()-seen[0]<45:raise ValueError('Dieser Einsatz wird von einem aktiven Disponenten betreut.')
                    # Under the room lock, disconnected owners can be replaced safely.
                    job['owner']=None
            if action=='upload_graphic':self.upload_graphic(member,data)
            else:engine.command(action,{**data,'_actor':member})
            return self.snapshot(member)

    def upload_graphic(self,member,data):
        try:raw=base64.b64decode(data.get('data',''),validate=True)
        except (ValueError,TypeError):raise ValueError('Ungültige Bilddatei.')
        if not 32<=len(raw)<=512*1024 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR':raise ValueError('Nur PNG-Dateien bis 512 KiB erlaubt.')
        width,height=struct.unpack('>II',raw[16:24])
        if not 1<=width<=4096 or not 1<=height<=4096:raise ValueError('Bildgröße maximal 4096 × 4096 Pixel.')
        name=str(data.get('name','')).strip()[:80]; author=str(data.get('author','')).strip()[:100];license=str(data.get('license','')).strip()[:250]
        if not name or not author or not license:raise ValueError('Name, Autor und Lizenz/Freigabe benötigt.')
        e=self.engine(member['room_id'])
        if len(e.state['graphics'])>=54:raise ValueError('Maximal 50 eigene Grafiken pro Sitzung.')
        id=secrets.token_hex(16)
        self.db.execute('INSERT INTO graphics_files VALUES (?,?,?)',(id,member['room_id'],raw));self.db.commit()
        e.state['graphics'].append({'id':id,'name':name,'author':author,'license':license,'source':str(data.get('source',''))[:500],'url':'/media/'+id+'.png'})
        e.log(f'{member["name"]} hat die Fahrzeuggrafik {name} hinzugefügt.','System');e.save()

    def media(self,id):
        with self.lock:
            row=self.db.execute('SELECT content FROM graphics_files WHERE id=?',(id,)).fetchone();return row[0] if row else None

    def tick(self,seconds):
        with self.lock:
            ids=[r[0] for r in self.db.execute('SELECT DISTINCT room_id FROM members WHERE last_seen>?',(time.time()-45,)).fetchall()]
            for id in ids:self.engine(id).tick(seconds)

    def close(self):
        for e in self.engines.values():e.db.close()
        self.db.close()
