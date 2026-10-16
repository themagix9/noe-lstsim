import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error
import test_fleet
from accounts import DEFAULTS

PASSWORD='Portal-Test-Password-2026!'
class Client:
    def __init__(self,port):
        self.base='http://127.0.0.1:'+str(port);self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar));self.csrf='';self.token=''
    def call(self,path,data=None,csrf=True,headers=None):
        h={'Content-Type':'application/json'}
        if self.token:h['Authorization']='Bearer '+self.token
        if csrf and self.csrf:h['X-CSRF-Token']=self.csrf
        h.update(headers or {})
        response=self.opener.open(urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=h),timeout=8)
        raw=response.read();body=json.loads(raw) if response.headers.get('Content-Type','').startswith('application/json') else raw
        if isinstance(body,dict) and body.get('csrf'):self.csrf=body['csrf']
        return body,response.headers

class PortalHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();root=Path(__file__).resolve().parents[1]
        cls.proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':cls.tmp.name,'ROUTING_ENABLED':'0','COOKIE_SECURE':'0','ADMIN_USERNAME':'portaladmin','ADMIN_PASSWORD':PASSWORD},stdout=subprocess.DEVNULL)
        for _ in range(80):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        cls.admin=Client(8081);cls.admin.call('/api/account/login',{'username':'portaladmin','password':PASSWORD})
    @classmethod
    def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=5);cls.tmp.cleanup()
    def setUp(self):
        self.admin.call('/api/admin/settings',{'settings':DEFAULTS})
        self.player=Client(8080);self.username='p_'+secrets.token_hex(6)
    def register(self):return self.player.call('/api/account/register',{'username':self.username,'display_name':'Spieler','password':PASSWORD,'role':'admin'})
    def create(self):
        room,_=self.player.call('/api/session/create',{'name':'Spieler','mode':'multi'});self.player.token=room['token'];return room
    def denied(self,client,path,data=None,status=403,**kw):
        with self.assertRaises(urllib.error.HTTPError) as error:client.call(path,data,**kw)
        self.assertEqual(error.exception.code,status)
    def test_global_usage_includes_guest_starts_and_survives_admin_delete(self):
        guest=Client(8080);room,_=guest.call('/api/session/create',{'name':'Statistik Gast','mode':'single'});guest.token=room['token']
        before,_=self.admin.call('/api/admin/dashboard')
        guest.call('/api/control',{'paused':False});guest.call('/api/control',{'paused':True})
        after,_=self.admin.call('/api/admin/dashboard');self.assertEqual(after['usage']['started'],before['usage']['started']+1)
        id=next(r['id'] for r in after['rooms'] if any(p['id']==room['player'] for p in r['players']))
        self.admin.call('/api/admin/delete-room',{'room':id,'confirm':True})
        deleted,_=self.admin.call('/api/admin/dashboard');self.assertEqual(deleted['usage']['created'],after['usage']['created']);self.assertEqual(deleted['usage']['started'],after['usage']['started'])
        self.assertIn('tracked_since',deleted['usage'])

    def test_delete_room_is_admin_only_csrf_protected_and_revokes_access(self):
        self.register();room=self.create();id=room['state']['session']['me']
        listing,_=self.player.call('/api/account/rooms');room_id=listing['rooms'][0]['id']
        payload={'room':room_id,'confirm':True}
        self.denied(Client(8081),'/api/admin/delete-room',payload)
        self.denied(self.player,'/api/admin/delete-room',payload,status=404)
        self.denied(self.admin,'/api/admin/delete-room',payload,csrf=False)
        self.denied(self.admin,'/api/admin/delete-room',{'room':room_id},status=400)
        self.admin.call('/api/admin/delete-room',payload)
        self.denied(self.player,'/api/state',status=401)
        self.denied(self.player,'/api/account/resume',{'membership':id})
        self.denied(Client(8080),'/api/session/join',{'name':'Zu spät','code':room['state']['session']['code']},status=400)
        rooms,_=self.player.call('/api/account/rooms');self.assertEqual(rooms['rooms'],[])
        self.denied(self.admin,'/api/admin/delete-room',payload,status=400)

    def test_map_page_sends_origin_to_external_tiles_but_admin_stays_private(self):
        _,public=self.player.call('/')
        _,admin=self.admin.call('/')
        self.assertEqual(public['Referrer-Policy'],'strict-origin-when-cross-origin')
        self.assertEqual(admin['Referrer-Policy'],'same-origin')

    def test_admin_isolation_and_no_role_escalation(self):
        me,_=self.register();self.assertEqual(me['user']['role'],'user')
        self.denied(self.player,'/api/admin/dashboard',status=404)
        self.denied(self.player,'/admin.html',status=404)
        stranger=Client(8081);self.denied(stranger,'/api/admin/dashboard',status=401)
        self.denied(stranger,'/api/account/login',{'username':self.username,'password':PASSWORD})
        self.denied(stranger,'/api/account/register',{'username':'badadmin','password':PASSWORD},status=404)
        self.denied(stranger,'/app.js',status=404)
    def test_cookie_flags_no_token_in_json_and_csrf_required(self):
        me,headers=self.register();cookie=headers['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie);self.assertNotIn('Domain=',cookie);self.assertNotIn('token',me)
        self.denied(self.admin,'/api/admin/settings',{'settings':{'registration_open':False}},csrf=False)
        self.denied(self.admin,'/api/admin/settings',{'settings':{}},headers={'Origin':'https://evil.example'})
        self.denied(self.player,'/api/account/logout',{},csrf=False)
        current,_=self.player.call('/api/account/me');self.assertEqual(current['user']['username'],self.username)
    def test_guest_chat_denied_and_account_chat_shared(self):
        guest=Client(8080);cred,_=guest.call('/api/session/create',{'name':'Gast','mode':'multi'});guest.token=cred['token']
        self.denied(guest,'/api/chat',{'text':'Gast'})
        self.register();joined,_=self.player.call('/api/session/join',{'name':'Spieler','code':cred['state']['session']['code']});self.player.token=joined['token']
        sent,_=self.player.call('/api/chat',{'text':'Registrierter Chat'});self.assertEqual(sent['chat'][-1]['text'],'Registrierter Chat')
        hidden,_=guest.call('/api/state');self.assertEqual(hidden['chat'],[])
        stolen=Client(8080);stolen.token=self.player.token;self.denied(stolen,'/api/state',status=401)
    def test_resume_only_own_membership_and_persisted_scene(self):
        self.register();room=self.create();self.player.call('/api/generate',{'kind':'transport'})
        listing,_=self.player.call('/api/account/rooms');self.assertEqual(len(listing['rooms']),1)
        resumed,_=self.player.call('/api/account/resume',{'membership':listing['rooms'][0]['membership']});self.assertEqual(len(resumed['state']['jobs']),1)
        other=Client(8080);other.call('/api/account/register',{'username':'o_'+secrets.token_hex(6),'password':PASSWORD})
        self.denied(other,'/api/account/resume',{'membership':listing['rooms'][0]['membership']})
    def test_public_maintenance_and_new_defaults(self):
        self.admin.call('/api/admin/settings',{'settings':{'maintenance_enabled':True,'maintenance_message':'Live-Test-Wartung','hour':13,'emergency_per_hour':11,'transports_enabled':False}})
        site,_=self.player.call('/api/site');self.assertEqual(site['maintenance']['message'],'Live-Test-Wartung');self.assertNotIn('users',site)
        self.register();room=self.create();self.assertEqual(room['state']['clock'],13*3600);self.assertEqual(room['state']['event_settings']['emergency_per_hour'],11);self.assertIsNone(room['state']['next_transport'])
        dashboard,_=self.admin.call('/api/admin/dashboard');self.assertGreaterEqual(dashboard['summary']['active_sessions'],1)
    def test_logout_and_disabled_accounts_cannot_use_saved_bearer(self):
        me,_=self.register();self.create();self.admin.call('/api/admin/user',{'id':me['user']['id'],'enabled':False})
        self.denied(self.player,'/api/state',status=401)
        self.denied(self.player,'/api/account/login',{'username':self.username,'password':PASSWORD})
    def test_registration_toggle(self):
        self.admin.call('/api/admin/settings',{'settings':{'registration_open':False}})
        self.denied(self.player,'/api/account/register',{'username':self.username,'password':PASSWORD})
    def test_admin_audit_does_not_expose_passwords_or_logins(self):
        me,_=self.register();self.admin.call('/api/admin/user',{'id':me['user']['id'],'new_password':'Changed-Secret-Password-2026!'})
        state,_=self.admin.call('/api/admin/dashboard');self.assertNotIn('Changed-Secret',json.dumps(state));self.assertNotIn('password_hash',json.dumps(state))
