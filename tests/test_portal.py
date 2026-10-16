import copy
import json
import secrets
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
import test_fleet
from sessions import Sessions
from accounts import password_hash,password_matches

class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/db';self.s=Sessions(self.path);self.a=self.s.accounts
        self.user=self.a.register({'username':'julian','display_name':'Julian','password':'My-Long-Password-2026!'})
        self.credential=self.s.create({'name':'Julian','mode':'single'},user_id=self.user['id']);self.member=self.s.member(self.credential['token'])
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def test_concurrent_password_work_has_bounded_memory_use(self):
        import threading
        active=0;peak=0;guard=threading.Lock()
        def derive(*args,**kwargs):
            nonlocal active,peak
            with guard:active+=1;peak=max(peak,active)
            time.sleep(.03)
            with guard:active-=1
            return b'fixed-test-digest'
        with patch('accounts.hashlib.scrypt',side_effect=derive):
            threads=[threading.Thread(target=password_hash,args=('Parallel-Password-2026!',)) for _ in range(8)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(2)
        self.assertEqual(peak,2);self.assertTrue(all(not thread.is_alive() for thread in threads))

    def test_password_salts_and_no_public_admin_role(self):
        self.assertEqual(self.user['role'],'user');self.assertNotIn('password_hash',self.user)
        one=password_hash('Long-Password-2026');two=password_hash('Long-Password-2026');self.assertNotEqual(one,two);self.assertTrue(password_matches('Long-Password-2026',one));self.assertFalse(password_matches('wrong-password',one))
    def test_duplicate_registration_does_not_hold_sqlite_write_lock(self):
        with self.assertRaises(ValueError):self.a.register({'username':'julian','password':'Another-Long-Password'})
        self.s.command(self.member,'generate',{'kind':'transport'})
        self.assertEqual(len(self.s.snapshot(self.member)['jobs']),1)

    def test_login_sessions_hashed_audience_and_csrf(self):
        login=self.a.login({'username':'JULIAN','password':'My-Long-Password-2026!'})
        self.assertEqual(self.a.authenticate(login['token'])['id'],self.user['id'])
        raw=self.a.db.execute('SELECT token_hash,csrf_hash FROM account_sessions').fetchone();self.assertNotEqual(raw[0],login['token']);self.assertNotEqual(raw[1],login['csrf'])
        with self.assertRaises(PermissionError):self.a.authenticate(login['token'],'admin')
        self.a.csrf(login['token'],login['csrf']);self.assertEqual(self.a.csrf_token(login['token']),login['csrf'])
        with self.assertRaises(PermissionError):self.a.csrf(login['token'],'forged')
        self.a.logout(login['token'])
        with self.assertRaises(PermissionError):self.a.authenticate(login['token'])
    def test_expired_and_disabled_account_denied(self):
        login=self.a.login({'username':'julian','password':'My-Long-Password-2026!'})
        self.a.db.execute('UPDATE account_sessions SET expires=0');self.a.db.commit()
        with self.assertRaises(PermissionError):self.a.authenticate(login['token'])
        admin=self.a.register({'username':'admin','display_name':'Admin','password':'Admin-Long-Password'},admin=True)
        self.a.update_user(admin,{'id':self.user['id'],'enabled':False})
        with self.assertRaises(PermissionError):self.a.login({'username':'julian','password':'My-Long-Password-2026!'})
        self.assertFalse(self.s.stream_touch(self.member))
    def test_restore_room_across_restart_and_other_account_cannot_take_it(self):
        self.s.command(self.member,'generate',{'kind':'transport'});job=self.s.engine(self.member['room_id']).state['jobs'][0]['id']
        old_member=copy.deepcopy(self.member);new=self.s.account_resume(self.user,self.member['id']);self.assertFalse(self.s.stream_touch(old_member))
        with self.assertRaises(PermissionError):self.s.member(self.credential['token'])
        self.s.close();self.s=Sessions(self.path);self.a=self.s.accounts
        resumed=self.s.account_resume(self.user,self.member['id']);self.assertEqual(resumed['state']['jobs'][0]['id'],job)
        other=self.a.register({'username':'other','display_name':'Other','password':'Other-Long-Password'})
        with self.assertRaises(PermissionError):self.s.account_resume(other,self.member['id'])
        self.assertEqual(self.s.account_rooms(other),[])
    def test_chat_registration_required_read_and_write(self):
        guest=self.s.member(self.s.create({'name':'Gast'})['token'])
        with self.assertRaises(PermissionError):self.s.command(guest,'chat',{'text':'Nein'})
        self.s.command(self.member,'chat',{'text':'Hallo'})
        room=self.s.db.execute('SELECT code FROM rooms WHERE id=?',(self.member['room_id'],)).fetchone()
        self.assertTrue(self.s.snapshot(self.member)['session']['chat_allowed'])
        self.assertEqual(self.s.snapshot(guest)['chat'],[])
    def test_link_requires_possession_and_cannot_steal_owned_membership(self):
        guest=self.s.create({'name':'Gast','mode':'single'});linked=self.s.account_link(self.user,guest['token']);self.assertTrue(linked['state']['session']['registered'])
        other=self.a.register({'username':'other','display_name':'Other','password':'Other-Long-Password'})
        with self.assertRaises(PermissionError):self.s.account_link(other,linked['token'])
    def test_globals_apply_to_new_rooms_and_explicit_existing(self):
        settings=self.a.update_settings({'username':'admin'},{'emergency_per_hour':12,'transport_per_hour':0,'transports_enabled':False,'hour':17,'speed':5,'blue_light_factor':.7})
        self.assertEqual(self.s.engine(self.member['room_id']).event_settings()['emergency_per_hour'],3)
        room=self.s.create({'name':'Neu','mode':'single'},user_id=self.user['id']);member=self.s.member(room['token']);state=self.s.snapshot(member)
        self.assertEqual(state['clock'],17*3600);self.assertEqual(state['speed'],5);self.assertEqual(state['event_settings']['emergency_per_hour'],12);self.assertIsNone(state['next_transport'])
        self.s.admin_apply_defaults(settings);self.assertEqual(self.s.engine(self.member['room_id']).event_settings()['emergency_per_hour'],12)
    def test_invalid_globals_and_registration_closed(self):
        for data in ({'blue_light_factor':0},{'emergency_per_hour':float('nan')},{'speed':2},{'maintenance_enabled':'yes'},{'unknown':True}):
            with self.assertRaises(ValueError):self.a.update_settings({'username':'admin'},data)
        self.a.update_settings({'username':'admin'},{'registration_open':False,'maintenance_enabled':True,'maintenance_message':'Wir bauen live.'})
        with self.assertRaises(PermissionError):self.a.register({'username':'neu','password':'Long-Password-2026'})
        self.assertEqual(self.s.snapshot(self.member)['site']['maintenance']['message'],'Wir bauen live.')
    def test_monitor_distinguishes_online_paused_running_and_saved(self):
        self.assertEqual(self.s.admin_monitor()['summary']['active_sessions'],1)
        self.assertEqual(self.s.admin_monitor()['summary']['running_sessions'],0)
        self.s.command(self.member,'control',{'paused':False});self.assertEqual(self.s.admin_monitor()['summary']['running_sessions'],1)
        self.s.command(self.member,'leave',{});monitor=self.s.admin_monitor();self.assertEqual(monitor['summary']['active_sessions'],0);self.assertEqual(monitor['summary']['sessions'],1)
    def test_statistics_survive_job_removal_reset_and_restart(self):
        engine=self.s.engine(self.member['room_id']);self.s.command(self.member,'generate',{'kind':'transport'});j=engine.state['jobs'][0];j.update(status='done',owner=self.member['id'],completed=engine.state['clock']+90);engine.save();engine.save()
        self.assertEqual(self.s.account_stats(self.user)['completed'],1)
        engine.state['jobs']=[];engine.save();self.s.close();self.s=Sessions(self.path);self.a=self.s.accounts
        self.assertEqual(self.s.account_stats(self.user)['transports_completed'],1)
    def test_completion_is_recorded_before_automatic_history_cleanup(self):
        engine=self.s.engine(self.member['room_id']);j=engine.new_job('transport')
        engine.state['jobs']=[{**copy.deepcopy(j),'id':f'history-{i}','status':'done','owner':self.member['id'],'completed':engine.state['clock']} for i in range(151)]
        engine.state['paused']=False;engine.tick(1)
        self.assertEqual(len(engine.state['jobs']),150);self.assertEqual(self.s.account_stats(self.user)['completed'],151)
    def test_playtime_counts_real_seconds_only_running_online(self):
        self.s.tick(10);self.assertEqual(self.s.account_stats(self.user)['play_seconds'],0)
        self.s.command(self.member,'control',{'paused':False,'speed':60});self.s.tick(2)
        self.assertEqual(self.s.account_stats(self.user)['play_seconds'],2)
        self.s.command(self.member,'leave',{});self.s.tick(10);self.assertEqual(self.s.account_stats(self.user)['play_seconds'],2)
    def test_password_change_revokes_all_logins_and_audit_redacts_password(self):
        login=self.a.login({'username':'julian','password':'My-Long-Password-2026!'})
        admin=self.a.register({'username':'admin','display_name':'Admin','password':'Admin-Long-Password'},admin=True)
        self.a.update_user(admin,{'id':self.user['id'],'new_password':'Replacement-Password-2026!'})
        with self.assertRaises(PermissionError):self.a.authenticate(login['token'])
        audit=json.dumps(self.s.admin_audit());self.assertNotIn('Replacement',audit)
        self.assertEqual(self.a.login({'username':'julian','password':'Replacement-Password-2026!'})['user']['id'],self.user['id'])
