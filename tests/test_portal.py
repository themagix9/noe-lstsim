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
    def test_global_usage_counts_guest_rooms_once_and_excludes_pause_and_offline(self):
        guest=self.s.member(self.s.create({'name':'Gast Eins','mode':'multi'})['token'])
        room=guest['room_id'];code=self.s.db.execute('SELECT code FROM rooms WHERE id=?',(room,)).fetchone()[0]
        second=self.s.member(self.s.join({'name':'Gast Zwei','code':code})['token'])
        registered=self.s.member(self.s.join({'name':'Konto','code':code},user_id=self.user['id'])['token'])
        self.assertEqual(self.s.usage_totals()['created'],2)
        self.assertEqual(self.s.usage_totals()['started'],0)
        self.s.tick(2);self.assertEqual(self.s.usage_totals()['real_seconds'],0)
        self.s.command(guest,'control',{'paused':False,'speed':60})
        self.assertEqual(self.s.usage_totals()['started'],1)
        # Multiple snapshots/tabs of the same membership must not multiply time.
        self.s.snapshot(second);self.s.snapshot(second)
        self.s.tick(2);usage=self.s.usage_totals()
        self.assertEqual(usage['real_seconds'],2);self.assertEqual(usage['sim_seconds'],120);self.assertEqual(usage['guest_seconds'],4);self.assertEqual(usage['player_seconds'],6)
        self.assertEqual(self.s.account_stats(self.user)['play_seconds'],2)
        self.s.command(guest,'control',{'paused':True});self.s.tick(8)
        self.s.command(guest,'control',{'paused':False,'speed':1});self.s.tick(3)
        usage=self.s.usage_totals();self.assertEqual(usage['started'],1);self.assertEqual(usage['real_seconds'],5);self.assertEqual(usage['sim_seconds'],123);self.assertEqual(usage['guest_seconds'],10);self.assertEqual(usage['player_seconds'],15)
        for member in (guest,second,registered):self.s.command(member,'leave',{})
        self.s.tick(10);self.assertEqual(self.s.usage_totals(),usage)
        self.s.admin_delete_room({'username':'admin'},{'room':room,'confirm':True});self.assertEqual(self.s.usage_totals(),usage)
        self.s.close();self.s=Sessions(self.path);self.a=self.s.accounts
        self.assertEqual(self.s.usage_totals(),usage)

    def test_guest_only_runtime_and_admin_resume_are_counted(self):
        guest=self.s.member(self.s.create({'name':'Gast ohne Konto','mode':'single'})['token'])
        self.s.admin_pause({'username':'admin'},{'room':guest['room_id'],'paused':False})
        self.s.tick(2);usage=self.s.usage_totals()
        self.assertEqual(usage['started'],1);self.assertEqual(usage['real_seconds'],2)
        self.assertEqual(usage['player_seconds'],2);self.assertEqual(usage['guest_seconds'],2)
        self.s.admin_pause({'username':'admin'},{'room':guest['room_id'],'paused':True});self.s.tick(10)
        self.s.admin_pause({'username':'admin'},{'room':guest['room_id'],'paused':False})
        self.assertEqual(self.s.usage_totals(),usage)

    def test_usage_import_uses_evidence_without_inventing_historical_guest_times(self):
        self.s.command(self.member,'control',{'paused':False});self.s.tick(3);self.s.command(self.member,'control',{'paused':True})
        guest=self.s.member(self.s.create({'name':'Unbekannter Altgast','mode':'single'})['token'])
        self.s.admin_delete_room({'username':'admin'},{'room':guest['room_id'],'confirm':True})
        self.s.close()
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TABLE simulation_usage');db.execute('DROP TABLE usage_metadata')
        self.s=Sessions(self.path);self.a=self.s.accounts
        usage=self.s.usage_totals();self.assertEqual(usage['created'],2);self.assertEqual(usage['started'],1)
        self.assertEqual(usage['real_seconds'],0);self.assertEqual(usage['guest_seconds'],0);self.assertEqual(usage['sim_seconds'],0)
        self.assertEqual(self.s.account_stats(self.user)['play_seconds'],3)
        self.s.initialize_usage();self.assertEqual(self.s.usage_totals(),usage)

    def test_admin_delete_revokes_room_and_preserves_statistics_and_other_rooms(self):
        room=self.member['room_id'];engine=self.s.engine(room)
        other=self.s.member(self.s.create({'name':'Andere Sitzung','mode':'single'},user_id=self.user['id'])['token'])
        self.s.command(self.member,'generate',{'kind':'transport'})
        job=engine.state['jobs'][0];job.update(status='done',owner=self.member['id'],completed=engine.state['clock']+90);engine.save()
        self.s.db.execute('INSERT INTO graphics_files VALUES(?,?,?)',('delete-picture',room,b'image'))
        self.s.db.execute('INSERT INTO player_usage VALUES(?,?,?)',(self.user['id'],room,42))
        self.s.db.execute('INSERT INTO account_events VALUES(?,?,?,?,?,?)',(room,job['id'],'call','',self.user['id'],time.time()));self.s.db.commit()
        before=self.s.account_stats(self.user)
        self.s.admin_delete_room({'username':'admin'},{'room':room,'confirm':True})
        self.assertEqual(self.s.account_stats(self.user),before)
        self.assertFalse(self.s.stream_touch(self.member));self.assertNotIn(room,self.s.engines)
        with self.assertRaises(PermissionError):self.s.member(self.credential['token'])
        with self.assertRaises(PermissionError):self.s.account_resume(self.user,self.member['id'])
        for action in ('snapshot','command','engine'):
            with self.assertRaises(PermissionError):
                if action=='snapshot':self.s.snapshot(self.member)
                elif action=='command':self.s.command(self.member,'generate',{'kind':'transport'})
                else:self.s.engine(room)
        for table in ('members','room_states','graphics_files'):
            self.assertEqual(self.s.db.execute('SELECT count(*) FROM '+table+' WHERE room_id=?',(room,)).fetchone()[0],0)
        self.assertEqual(self.s.snapshot(other)['session']['me'],other['id'])
        self.assertEqual([r['id'] for r in self.s.account_rooms(self.user)],[other['room_id']])
        self.assertEqual(self.s.admin_audit()[0]['action'],'room_delete')
        self.s.close();self.s=Sessions(self.path);self.a=self.s.accounts
        self.assertEqual(self.s.account_stats(self.user),before)
        self.assertNotIn(room,[r['id'] for r in self.s.admin_monitor()['rooms']])

    def test_delete_saved_unloaded_room_and_reject_late_dispatch(self):
        room=self.member['room_id'];engine=self.s.engine(room)
        engine.db.close();self.s.engines.pop(room)
        self.s.admin_delete_room({'username':'admin'},{'room':room,'confirm':True})
        self.assertNotIn(room,self.s.engines)
        self.assertIsNone(self.s.db.execute('SELECT value FROM room_states WHERE room_id=?',(room,)).fetchone())

    def test_dispatch_waiting_for_route_cannot_recreate_deleted_room(self):
        room=self.member['room_id'];engine=self.s.engine(room)
        self.s.command(self.member,'generate',{'kind':'transport'})
        job=engine.state['jobs'][0];vehicle=next(v for v in engine.state['vehicles'] if v['callsign']=='77/002')
        def delete_during_routing(journeys):
            self.s.admin_delete_room({'username':'admin'},{'room':room,'confirm':True})
            return {id:{} for id,_,_ in journeys}
        with patch.object(engine.router,'enabled',True),patch.object(engine.router,'wait_routes',side_effect=delete_during_routing) as routes:
            with self.assertRaises(PermissionError):self.s.command(self.member,'dispatch',{'job':job['id'],'vehicles':[vehicle['id']]})
            routes.assert_called_once()
        self.assertNotIn(room,self.s.engines)
        self.assertIsNone(self.s.db.execute('SELECT value FROM room_states WHERE room_id=?',(room,)).fetchone())

    def test_admin_delete_requires_explicit_confirmation(self):
        room=self.member['room_id']
        for confirm in (None,False,'true',1):
            with self.assertRaises(ValueError):self.s.admin_delete_room({'username':'admin'},{'room':room,'confirm':confirm})
        self.assertEqual(self.s.snapshot(self.member)['session']['me'],self.member['id'])
        with self.assertRaises(ValueError):self.s.admin_delete_room({'username':'admin'},{'room':'absent','confirm':True})

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
