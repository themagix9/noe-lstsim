"""Account-linked saved rooms, aggregate statistics and administrator monitoring."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import time

class SessionPortal:
    def portal_schema(self):
        if 'user_id' not in {r[1] for r in self.db.execute('PRAGMA table_info(members)')}:self.db.execute('ALTER TABLE members ADD COLUMN user_id TEXT')
        self.db.executescript('''
        CREATE INDEX IF NOT EXISTS member_user ON members(user_id);
        CREATE TABLE IF NOT EXISTS archived_member_users(member_id TEXT PRIMARY KEY,user_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS account_events(room_id TEXT,job_id TEXT,event TEXT,unit TEXT,user_id TEXT,at REAL,PRIMARY KEY(room_id,job_id,event,unit));
        CREATE TABLE IF NOT EXISTS player_usage(user_id TEXT,room_id TEXT,seconds REAL,PRIMARY KEY(user_id,room_id));
        ''');self.db.commit()
    def account_link(self,user,token):
        with self.lock:
            member=self.member(token,touch=False)
            if member.get('user_id') and member['user_id']!=user['id']:raise PermissionError('Sitzung gehört einem anderen Konto.')
            existing=self.db.execute('SELECT id FROM members WHERE user_id=? AND room_id=? AND id!=?',(user['id'],member['room_id'],member['id'])).fetchone()
            if existing:raise ValueError('Dein Konto ist bereits in dieser Sitzung. Über Meine Sitzungen fortsetzen.')
            self.db.execute('UPDATE members SET user_id=? WHERE id=?',(user['id'],member['id']));self.db.commit()
            return self.account_resume(user,member['id'])
    def account_resume(self,user,member_id):
        with self.lock:
            row=self.db.execute('SELECT id FROM members WHERE id=? AND user_id=?',(member_id,user['id'])).fetchone()
            if not row:raise PermissionError('Kein Zugriff auf diesen Spielstand.')
            token=secrets.token_urlsafe(32)
            self.db.execute('UPDATE members SET token_hash=?,last_seen=? WHERE id=?',(hashlib.sha256(token.encode()).hexdigest(),time.time(),member_id));self.db.commit()
            member=self.member(token);return {'token':token,'player':member_id,'state':self.snapshot(member)}
    def account_rooms(self,user):
        with self.lock:
            rows=self.db.execute('SELECT m.id,r.id,r.title,r.mode,r.created,m.host,m.last_seen FROM members m JOIN rooms r ON r.id=m.room_id WHERE m.user_id=? ORDER BY m.last_seen DESC LIMIT 100',(user['id'],)).fetchall()
            return [{'membership':r[0],'id':r[1],'title':r[2],'mode':r[3],'created':r[4],'host':bool(r[5]),'last_seen':r[6]} for r in rows]
    def account_stats(self,user=None):
        with self.lock:
            where='WHERE coalesce(m.user_id,a.user_id)=?' if user else '';args=(user['id'],) if user else ()
            row=self.db.execute('SELECT count(*),coalesce(sum(c.kind=\'emergency\'),0),coalesce(sum(c.kind=\'transport\'),0),coalesce(sum(c.duration),0) FROM completed_incidents c LEFT JOIN members m ON m.id=c.owner_member LEFT JOIN archived_member_users a ON a.member_id=c.owner_member '+where,args).fetchone()
            events=dict(self.db.execute('SELECT event,count(*) FROM account_events '+('WHERE user_id=?' if user else '')+' GROUP BY event',args).fetchall())
            seconds=self.db.execute('SELECT coalesce(sum(seconds),0) FROM player_usage '+('WHERE user_id=?' if user else ''),args).fetchone()[0]
            return {'completed':row[0],'emergencies_completed':row[1],'transports_completed':row[2],'incident_seconds':row[3],'calls_taken':events.get('call',0),'dispatches':events.get('dispatch',0),'play_seconds':seconds}
    def record_account_event(self,member,action,data,engine):
        if not member.get('user_id'):return
        if action=='accept':rows=[(data['id'],'call','')]
        elif action=='dispatch':rows=[(data['job'],'dispatch',v['id']) for v in engine.state['vehicles'] if v.get('job')==data['job'] and v['id'] in data.get('vehicles',[])]
        else:return
        for job,event,unit in rows:self.db.execute('INSERT OR IGNORE INTO account_events VALUES(?,?,?,?,?,?)',(member['room_id'],job,event,unit,member['user_id'],time.time()))
        self.db.commit()
    def apply_defaults(self,engine,settings=None):
        with engine.lock:
            s=settings or self.accounts.settings();split=engine.state['setup'].get('workflow')=='split'
            engine.state['setup'].update(blue_light_factor=s['blue_light_factor'],helicopter_speed_factor=s['helicopter_speed_factor'])
            engine.configure_events({'emergency_per_hour':s['split_emergency_per_hour'] if split else s['emergency_per_hour'],'transport_per_hour':s['split_transport_per_hour'] if split else s['transport_per_hour'],'transports_enabled':s['transports_enabled']})
            engine.save()
    def admin_apply_defaults(self,settings):
        with self.lock:
            ids=[r[0] for r in self.db.execute('SELECT id FROM rooms')]
            for id in ids:self.apply_defaults(self.engine(id),settings)
            return len(ids)
    def admin_monitor(self):
        with self.lock:
            now=time.time();rooms=[]
            for r in self.db.execute('SELECT id,code,title,mode,created FROM rooms ORDER BY created DESC').fetchall():
                people=self.db.execute('SELECT id,name,host,last_seen,role,user_id FROM members WHERE room_id=?',(r[0],)).fetchall()
                last=max([p[3] for p in people] or [0]);active=last>now-45
                engine=self.engines.get(r[0])
                if engine:
                    with engine.lock:
                        summary=self.room_summary(engine.state)
                else:
                    row=self.db.execute('SELECT value FROM room_states WHERE room_id=?',(r[0],)).fetchone();summary=self.room_summary(json.loads(row[0])) if row else {}
                rooms.append({'id':r[0],'code':r[1] if r[3]=='multi' else None,'title':r[2],'mode':r[3],'created':r[4],'last_seen':last,'active':active,'running':active and not summary.get('paused',True),**summary,
                    'players':[{'id':p[0],'name':p[1],'host':bool(p[2]),'online':p[3]>now-45,'role':p[4],'registered':bool(p[5])} for p in people]})
            storage=shutil.disk_usage(Path(self.path).parent)
            db_bytes=sum(Path(self.path+suffix).stat().st_size for suffix in ('','-wal','-shm') if Path(self.path+suffix).exists())
            audit=self.admin_audit()
            return {'updated_at':now,'uptime_seconds':now-self.accounts.started,'rooms':rooms,'summary':{'sessions':len(rooms),'active_sessions':sum(r['active'] for r in rooms),'running_sessions':sum(r['running'] for r in rooms),'online_players':sum(sum(p['online'] for p in r['players']) for r in rooms),'users':self.accounts.user_count(),'loaded_simulations':len(self.engines),'database_bytes':db_bytes,'disk_free_bytes':storage.free},'stats':self.account_stats(),'settings':self.accounts.settings(),'audit':audit}
    def admin_audit(self):
        with self.accounts.lock:
            return [dict(id=r[0],at=r[1],actor=r[2],action=r[3],detail=json.loads(r[4])) for r in self.accounts.db.execute('SELECT * FROM admin_audit ORDER BY id DESC LIMIT 50').fetchall()]
    def room_summary(self,s):
        return {'paused':s['paused'],'clock':s['clock'],'speed':s['speed'],'centre':s.get('setup',{}).get('centre'),'dispo':s.get('setup',{}).get('dispo'),'open_incidents':sum(j['status']!='done' for j in s['jobs']),'open_radio':sum(c['state']!='closed' for c in s.get('radio_calls',[]))}
    def admin_pause(self,actor,data):
        if not isinstance(data.get('paused'),bool):raise ValueError('Pause ein- oder ausschalten.')
        with self.lock:
            if not self.db.execute('SELECT 1 FROM rooms WHERE id=?',(data.get('room'),)).fetchone():raise ValueError('Sitzung nicht gefunden.')
            self.engine(data['room']).command('control',{'paused':data['paused']})
        self.accounts.audit(actor,'room_pause',{'room':data['room'],'paused':data['paused']})

    def require_room(self,member):
        if not self.db.execute('SELECT 1 FROM rooms WHERE id=?',(member['room_id'],)).fetchone():
            raise PermissionError('Diese Sitzung wurde beendet oder gelöscht.')

    def admin_delete_room(self,actor,data):
        room=data.get('room')
        if not isinstance(room,str) or not room:raise ValueError('Sitzung auswählen.')
        if data.get('confirm') is not True:raise ValueError('Löschen der Sitzung ausdrücklich bestätigen.')
        with self.lock:
            row=self.db.execute('SELECT title FROM rooms WHERE id=?',(room,)).fetchone()
            if not row:raise ValueError('Sitzung nicht gefunden.')
            engine=self.engines.get(room)
            if engine:
                with engine.lock:engine.save()
            # Keep only the account attribution needed by historical statistics.
            # Room state, participants, bearer tokens, chat and uploads are removed.
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO archived_member_users SELECT id,user_id FROM members WHERE room_id=? AND user_id IS NOT NULL AND id IN (SELECT owner_member FROM completed_incidents WHERE room_id=?)',(room,room))
                self.db.execute('DELETE FROM graphics_files WHERE room_id=?',(room,))
                self.db.execute('DELETE FROM members WHERE room_id=?',(room,))
                self.db.execute('DELETE FROM room_states WHERE room_id=?',(room,))
                self.db.execute('DELETE FROM rooms WHERE id=?',(room,))
                self.db.execute('INSERT INTO admin_audit(at,actor,action,detail) VALUES(?,?,?,?)',(time.time(),actor['username'],'room_delete',json.dumps({'room':room,'title':row[0]},ensure_ascii=False)))
            if engine:
                self.engines.pop(room)
                engine.db.close()
