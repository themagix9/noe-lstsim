"""Same-origin account API and an isolated admin listener on port 8081."""
from collections import defaultdict,deque
from http.cookies import SimpleCookie,CookieError
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse

attempts=defaultdict(deque);attempt_lock=threading.Lock()

class PortalHTTP:
    admin_portal=False
    def login_cookie_name(self):return ('__Host-' if os.environ.get('COOKIE_SECURE','1')!='0' else 'dev_')+('noe_admin' if self.admin_portal else 'noe_account')
    def login_token(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except CookieError:return ''
        item=cookie.get(self.login_cookie_name());return item.value if item else ''
    def account_user(self,optional=False):
        token=self.login_token()
        if optional and not token:return None
        try:return self.sessions.accounts.authenticate(token,'admin' if self.admin_portal else 'player')
        except PermissionError:
            if optional:return None
            raise
    def auth_cookie(self,token,max_age):
        secure='; Secure' if os.environ.get('COOKIE_SECURE','1')!='0' else ''
        return self.login_cookie_name()+'='+token+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+str(max_age)+secure
    def csrf_check(self):self.sessions.accounts.csrf(self.login_token(),self.headers.get('X-CSRF-Token',''),'admin' if self.admin_portal else 'player')
    def auth_limit(self,data):
        # Use the connection IP, never an unauthenticated forwarded header. Bound both
        # a tunnel connection and each login name to prevent password guessing.
        now=time.monotonic();ip=self.client_address[0];name=str(data.get('username','')).strip().lower()[:64]
        with attempt_lock:
            for key in list(attempts):
                if not attempts[key] or now-attempts[key][-1]>300:del attempts[key]
            for key,maximum in ((('ip',ip),120),(('name',name),10)):
                window=attempts[key]
                while window and now-window[0]>300:window.popleft()
                if len(window)>=maximum:raise PermissionError('Zu viele Anmeldeversuche. In fünf Minuten erneut versuchen.')
            if len(attempts)>10000:raise PermissionError('Anmeldung ausgelastet. Bitte später erneut versuchen.')
            attempts[('ip',ip)].append(now);attempts[('name',name)].append(now)
    def portal_get(self,path):
        if path=='/api/site' and not self.admin_portal:return self.json_response(self.sessions.accounts.public_config())
        if path=='/api/account/me':
            user=self.account_user(optional=True)
            return self.json_response({'user':user,'csrf':self.sessions.accounts.csrf_token(self.login_token()) if user else None})
        if path in ('/api/account/rooms','/api/account/stats') and not self.admin_portal:
            user=self.account_user();return self.json_response({'rooms':self.sessions.account_rooms(user)} if path.endswith('rooms') else self.sessions.account_stats(user))
        if path=='/api/admin/catalog' and self.admin_portal:
            self.account_user()
            from catalog import ZONES,CENTRES
            return self.json_response({'zones':ZONES,'centres':CENTRES})
        if path=='/api/admin/dashboard' and self.admin_portal:
            self.account_user();return self.json_response(self.sessions.admin_monitor())
        if path=='/api/admin/users' and self.admin_portal:
            self.account_user();return self.json_response({'users':self.sessions.accounts.users()})
        return self.json_response({'error':'Nicht gefunden'},404)
    def portal_post(self,path,data):
        accounts=self.sessions.accounts;audience='admin' if self.admin_portal else 'player'
        if path in ('/api/account/register','/api/account/login'):
            if path.endswith('register') and self.admin_portal:return self.json_response({'error':'Keine öffentliche Administratorregistrierung.'},404)
            self.auth_limit(data)
            if path.endswith('register'):accounts.register(data)
            result=accounts.login(data,audience)
            self.respond(json.dumps({'user':result['user'],'csrf':result['csrf']},ensure_ascii=False).encode(),'application/json; charset=utf-8',headers={'Set-Cookie':self.auth_cookie(result['token'],result['max_age'])});return
        user=self.account_user();self.csrf_check()
        if path=='/api/account/logout':
            accounts.logout(self.login_token());self.respond(b'{"ok":true}','application/json',headers={'Set-Cookie':self.auth_cookie('',0)});return
        if path=='/api/account/password':
            accounts.change_password(user,data.get('current_password'),data.get('new_password'));self.respond(b'{"ok":true}','application/json',headers={'Set-Cookie':self.auth_cookie('',0)});return
        if not self.admin_portal:
            if path=='/api/account/resume':return self.json_response(self.sessions.account_resume(user,data.get('membership')))
            if path=='/api/account/link':return self.json_response(self.sessions.account_link(user,data.get('token','')))
        else:
            if path=='/api/admin/settings':
                apply=data.get('apply_existing',False)
                if not isinstance(apply,bool):raise ValueError('Übernahme für bestehende Sitzungen ungültig.')
                settings=accounts.update_settings(user,data.get('settings',{}));changed=self.sessions.admin_apply_defaults(settings) if apply else 0
                self.notify_live();return self.json_response({'settings':settings,'changed_sessions':changed})
            if path=='/api/admin/delete-room':self.sessions.admin_delete_room(user,data);self.notify_live();return self.json_response({'ok':True})
            if path=='/api/admin/pause':self.sessions.admin_pause(user,data);self.notify_live();return self.json_response({'ok':True})
            if path=='/api/admin/user':return self.json_response({'user':accounts.update_user(user,data)})
        return self.json_response({'error':'Nicht gefunden'},404)
