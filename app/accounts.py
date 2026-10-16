"""Persistent local accounts and host-scoped login sessions. No plaintext passwords/tokens."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time

PASSWORD_SLOTS=threading.BoundedSemaphore(2)

DEFAULTS={'registration_open':True,'maintenance_enabled':False,'maintenance_message':'Am Simulator wird gerade live gearbeitet. Es kann zu kurzen Unterbrechungen kommen.',
          'centre':'Mödling','dispo':'05','hour':8,'speed':1,'emergency_per_hour':3,'transport_per_hour':4,'transports_enabled':True,
          'split_emergency_per_hour':6,'split_transport_per_hour':6,'blue_light_factor':.85,'helicopter_speed_factor':1.15}

def password_hash(password,salt=None):
    if not isinstance(password,str) or not 12<=len(password)<=128:raise ValueError('Passwort: 12 bis 128 Zeichen.')
    salt=salt or secrets.token_hex(16)
    if not PASSWORD_SLOTS.acquire(timeout=5):raise ValueError('Anmeldung ausgelastet. Bitte erneut versuchen.')
    try:digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=32768,r=8,p=1,maxmem=64*1024*1024).hex()
    finally:PASSWORD_SLOTS.release()
    return 'scrypt$'+salt+'$'+digest

def password_matches(password,stored):
    try:return hmac.compare_digest(password_hash(password,stored.split('$')[1]),stored)
    except (ValueError,TypeError,IndexError):return False

def token_hash(value):return hashlib.sha256(str(value).encode()).hexdigest()

class Accounts:
    def __init__(self,path):
        self.path=path;self.lock=threading.RLock();self.started=time.time()
        self.db=sqlite3.connect(path,check_same_thread=False);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=5000');self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE COLLATE NOCASE,display_name TEXT,password_hash TEXT,role TEXT NOT NULL DEFAULT 'user',enabled INTEGER NOT NULL DEFAULT 1,created REAL,last_login REAL);
        CREATE TABLE IF NOT EXISTS account_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT,csrf_hash TEXT,expires REAL,audience TEXT);
        CREATE TABLE IF NOT EXISTS site_settings(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT);
        CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at REAL,actor TEXT,action TEXT,detail TEXT);
        ''');self.db.commit()
        self.dummy=password_hash(secrets.token_urlsafe(24))
        username=os.environ.get('ADMIN_USERNAME','').strip();password=os.environ.get('ADMIN_PASSWORD','')
        if username and password:
            with self.lock:
                # Never promote a pre-existing public registration with a matching username.
                if not self.db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
                    if self.db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():raise RuntimeError('ADMIN_USERNAME ist bereits ein Spielerkonto. Anderen Bootstrap-Namen wählen.')
                    self.register({'username':username,'display_name':'Administration','password':password},admin=True)
    def public_user(self,row):return {k:row[k] for k in ('id','username','display_name','role','enabled','created','last_login')}
    def settings(self):
        with self.lock:
            row=self.db.execute('SELECT value FROM site_settings WHERE id=1').fetchone()
            return {**DEFAULTS,**(json.loads(row[0]) if row else {})}
    def public_config(self):
        s=self.settings();return {'registration_open':s['registration_open'],'maintenance':{'enabled':s['maintenance_enabled'],'message':s['maintenance_message']},'defaults':{k:s[k] for k in ('centre','dispo','hour')}}
    def register(self,data,admin=False):
        username=str(data.get('username','')).strip().lower();name=str(data.get('display_name') or username).strip()
        if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{2,31}',username):raise ValueError('Benutzername: 3–32 Buchstaben, Zahlen, Punkt, Unterstrich oder Bindestrich.')
        if not 2<=len(name)<=30 or any(ord(c)<32 for c in name):raise ValueError('Anzeigename: 2–30 Zeichen.')
        encoded=password_hash(data.get('password'))
        with self.lock:
            if not admin and not self.settings()['registration_open']:raise PermissionError('Registrierung ist derzeit geschlossen.')
            id=secrets.token_hex(16)
            try:self.db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?,?)',(id,username,name,encoded,'admin' if admin else 'user',1,time.time(),None));self.db.commit()
            except sqlite3.IntegrityError:
                self.db.rollback();raise ValueError('Benutzername ist bereits vergeben.')
            return self.user(id)
    def user(self,id):
        with self.lock:
            row=self.db.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone()
            return self.public_user(row) if row else None
    def login(self,data,audience='player'):
        username=str(data.get('username','')).strip().lower()
        with self.lock:row=self.db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        valid=password_matches(data.get('password'),row['password_hash'] if row else self.dummy)
        if not row or not valid or not row['enabled'] or audience=='admin' and row['role']!='admin':raise PermissionError('Benutzername oder Passwort ungültig.')
        token=secrets.token_urlsafe(40);csrf=hmac.new(token.encode(),b'csrf',hashlib.sha256).hexdigest();ttl=43200 if audience=='admin' else 30*86400
        with self.lock:
            self.db.execute('DELETE FROM account_sessions WHERE expires<?',(time.time(),))
            self.db.execute('INSERT INTO account_sessions VALUES(?,?,?,?,?)',(token_hash(token),row['id'],token_hash(csrf),time.time()+ttl,audience))
            self.db.execute('UPDATE users SET last_login=? WHERE id=?',(time.time(),row['id']));self.db.commit()
        return {'token':token,'csrf':csrf,'max_age':ttl,'user':self.user(row['id'])}
    def authenticate(self,token,audience='player'):
        if not token or len(token)>200:raise PermissionError('Bitte anmelden.')
        with self.lock:
            row=self.db.execute('SELECT u.* FROM account_sessions a JOIN users u ON a.user_id=u.id WHERE a.token_hash=? AND a.expires>? AND a.audience=? AND u.enabled=1',(token_hash(token),time.time(),audience)).fetchone()
            if not row or audience=='admin' and row['role']!='admin':raise PermissionError('Anmeldung abgelaufen oder nicht berechtigt.')
            return self.public_user(row)
    def csrf(self,token,value,audience='player'):
        self.authenticate(token,audience)
        with self.lock:row=self.db.execute('SELECT csrf_hash FROM account_sessions WHERE token_hash=?',(token_hash(token),)).fetchone()
        if not value or not row or not hmac.compare_digest(row[0],token_hash(value)):raise PermissionError('Sicherheitsnachweis fehlt. Seite neu laden und erneut anmelden.')
    def csrf_token(self,token):
        return hmac.new(token.encode(),b'csrf',hashlib.sha256).hexdigest()
    def logout(self,token):
        with self.lock:self.db.execute('DELETE FROM account_sessions WHERE token_hash=?',(token_hash(token),));self.db.commit()
    def change_password(self,user,current,new):
        with self.lock:row=self.db.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()
        if not password_matches(current,row[0]):raise PermissionError('Aktuelles Passwort ungültig.')
        encoded=password_hash(new)
        with self.lock:
            self.db.execute('UPDATE users SET password_hash=? WHERE id=?',(encoded,user['id']));self.db.execute('DELETE FROM account_sessions WHERE user_id=?',(user['id'],));self.db.commit()
    def audit(self,actor,action,detail):
        with self.lock:
            self.db.execute('INSERT INTO admin_audit(at,actor,action,detail) VALUES(?,?,?,?)',(time.time(),actor['username'],action,json.dumps(detail,ensure_ascii=False)));self.db.commit()
    def update_settings(self,actor,data):
        from catalog import CENTRES,ZONES
        import math
        if not isinstance(data,dict):raise ValueError('Einstellungen als JSON-Objekt übergeben.')
        s=self.settings()
        for key,value in data.items():
            if key not in DEFAULTS:raise ValueError('Unbekannte globale Einstellung: '+key)
            if isinstance(DEFAULTS[key],bool):
                if not isinstance(value,bool):raise ValueError('Ein-/Aus-Einstellung ungültig.')
            elif key=='maintenance_message':
                if not isinstance(value,str) or not 1<=len(value.strip())<=500:raise ValueError('Wartungsnachricht: 1–500 Zeichen.')
                value=value.strip()
            elif key=='centre':
                if value not in CENTRES:raise ValueError('Leitstellenstandort ungültig.')
            elif key=='dispo':
                if value not in {z['id'] for z in ZONES}:raise ValueError('Dispozone ungültig.')
            else:
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Numerische Einstellung ungültig.')
                if key=='hour' and (not 0<=value<=23 or int(value)!=value):raise ValueError('Stunde 0–23 wählen.')
                if key=='speed' and value not in (1,5,15,60):raise ValueError('Geschwindigkeit ungültig.')
                if key.endswith('_per_hour') and not 0<=value<=120:raise ValueError('Frequenz: 0–120 pro Stunde.')
                if key=='blue_light_factor' and not .5<=value<=1:raise ValueError('Signalfaktor: 0,5–1.')
                if key=='helicopter_speed_factor' and not 1<=value<=2:raise ValueError('Helifaktor: 1–2.')
            s[key]=value
        with self.lock:self.db.execute('INSERT OR REPLACE INTO site_settings VALUES(1,?)',(json.dumps(s),));self.db.commit()
        self.audit(actor,'settings',data);return s
    def user_count(self):
        with self.lock:return self.db.execute('SELECT count(*) FROM users').fetchone()[0]
    def users(self):
        with self.lock:return [self.public_user(r) for r in self.db.execute('SELECT * FROM users ORDER BY created DESC LIMIT 500')]
    def update_user(self,actor,data):
        target=self.user(data.get('id'))
        if not target:raise ValueError('Benutzer nicht gefunden.')
        enabled=data.get('enabled',bool(target['enabled']))
        if not isinstance(enabled,bool):raise ValueError('Kontostatus ungültig.')
        if target['role']=='admin' and not enabled:raise ValueError('Administratorkonten werden hier nicht gesperrt.')
        encoded=password_hash(data['new_password']) if data.get('new_password') else None
        with self.lock:
            self.db.execute('UPDATE users SET enabled=? WHERE id=?',(int(enabled),target['id']))
            if encoded:self.db.execute('UPDATE users SET password_hash=? WHERE id=?',(encoded,target['id']))
            if encoded or not enabled:self.db.execute('DELETE FROM account_sessions WHERE user_id=?',(target['id'],))
            self.db.commit()
        self.audit(actor,'user_update',{'id':target['id'],'enabled':enabled,'password_reset':bool(encoded)})
        return self.user(target['id'])
    def close(self):self.db.close()
