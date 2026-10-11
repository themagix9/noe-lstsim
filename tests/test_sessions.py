import base64
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from engine import seed
from sessions import Sessions

PNG='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB/8AAAAASUVORK5CYII='

class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=str(Path(self.temp.name)/'db.sqlite3');self.s=Sessions(self.path)
        self.auth=self.s.create({'name':'Julian','title':'Test'});self.host=self.s.member(self.auth['token']);self.code=self.s.snapshot(self.host)['session']['code']
        self.guest_auth=self.s.join({'name':'Lara','code':self.code});self.guest=self.s.member(self.guest_auth['token'])
    def tearDown(self):self.s.close();self.temp.cleanup()
    def job(self):
        self.s.command(self.host,'generate',{'kind':'transport'});return self.s.snapshot(self.host)['jobs'][-1]
    def test_leave_pauses_only_private_simulation(self):
        auth=self.s.create({'name':'Solo','mode':'single'});member=self.s.member(auth['token'])
        self.s.command(member,'control',{'paused':False})
        self.s.command(member,'leave',{})
        self.assertTrue(self.s.engine(member['room_id']).state['paused'])
        self.s.command(self.host,'control',{'paused':False})
        self.s.command(self.guest,'leave',{})
        self.assertFalse(self.s.engine(self.host['room_id']).state['paused'])

    def test_players_share_state_and_owner(self):
        j=self.job();self.s.command(self.guest,'claim',{'id':j['id']})
        self.assertEqual(self.s.snapshot(self.host)['jobs'][-1]['owner'],self.guest['id'])
        self.assertEqual(len(self.s.snapshot(self.host)['session']['players']),2)
    def test_other_player_cannot_dispatch_claimed_job(self):
        j=self.job();self.s.command(self.guest,'claim',{'id':j['id']})
        v=next(v for v in self.s.snapshot(self.host)['vehicles'] if v['type']=='KTW')
        with self.assertRaises(ValueError):self.s.command(self.host,'dispatch',{'job':j['id'],'vehicles':[v['id']]})
        self.assertIsNone(next(x for x in self.s.snapshot(self.host)['vehicles'] if x['id']==v['id'])['job'])
    def test_concurrent_claim_has_one_winner(self):
        j=self.job();barrier=threading.Barrier(2);wins=[]
        def claim(player):
            barrier.wait()
            try:self.s.command(player,'claim',{'id':j['id']});wins.append(player['id'])
            except ValueError:pass
        a=threading.Thread(target=claim,args=(self.host,));b=threading.Thread(target=claim,args=(self.guest,));a.start();b.start();a.join();b.join()
        self.assertEqual(len(wins),1);self.assertEqual(self.s.snapshot(self.host)['jobs'][-1]['owner'],wins[0])
    def test_rooms_are_isolated(self):
        other=self.s.member(self.s.create({'name':'Anderer','title':'Andere Runde'})['token']);j=self.job()
        self.assertEqual(self.s.snapshot(other)['jobs'],[])
        with self.assertRaises(ValueError):self.s.command(other,'claim',{'id':j['id']})
    def test_guest_cannot_change_fleet_or_reset(self):
        v=self.s.snapshot(self.host)['vehicles'][0]
        for action,data in [('vehicle',v),('reset',{}),('upload_graphic',{})]:
            with self.assertRaises(PermissionError):self.s.command(self.guest,action,data)
    def test_disconnected_owner_can_be_replaced(self):
        j=self.job();self.s.command(self.guest,'claim',{'id':j['id']});self.s.command(self.guest,'leave',{});self.s.command(self.host,'claim',{'id':j['id']})
        self.assertEqual(self.s.snapshot(self.host)['jobs'][-1]['owner'],self.host['id'])
    def test_release_and_handover(self):
        j=self.job();self.s.command(self.host,'claim',{'id':j['id']});self.s.command(self.host,'release',{'id':j['id']});self.s.command(self.guest,'claim',{'id':j['id']})
        self.assertEqual(self.s.snapshot(self.host)['jobs'][-1]['owner'],self.guest['id'])
    def test_chat_is_shared_and_isolated(self):
        self.s.command(self.guest,'chat',{'text':'Ich übernehme den Transport.'});self.assertEqual(self.s.snapshot(self.host)['chat'][-1]['name'],'Lara')
        other=self.s.member(self.s.create({'name':'Andere'})['token']);self.assertEqual(self.s.snapshot(other)['chat'],[])
    def test_persistence_keeps_token_room_and_claim(self):
        j=self.job();self.s.command(self.guest,'claim',{'id':j['id']});self.s.close();self.s=Sessions(self.path)
        host=self.s.member(self.auth['token']);self.assertEqual(self.s.snapshot(host)['session']['code'],self.code);self.assertEqual(self.s.snapshot(host)['jobs'][-1]['owner'],self.guest['id'])
    def test_invalid_token_cannot_read_room(self):
        with self.assertRaises(PermissionError):self.s.member('invalid')
    def test_png_upload_and_assignment(self):
        self.s.command(self.host,'upload_graphic',{'name':'Eigene Grafik','author':'Test','license':'Eigene Zeichnung','data':PNG})
        state=self.s.snapshot(self.host);g=state['graphics'][-1];self.assertTrue(self.s.media(g['id']).startswith(b'\x89PNG'))
        v=copy.deepcopy(state['vehicles'][0]);v['graphic']=g['id'];self.s.command(self.host,'vehicle',v)
        self.assertEqual(self.s.snapshot(self.host)['vehicles'][0]['graphic'],g['id'])
    def test_reject_non_png_and_unknown_graphic(self):
        with self.assertRaises(ValueError):self.s.command(self.host,'upload_graphic',{'name':'Fake','author':'X','license':'X','data':base64.b64encode(b'<svg/>').decode()})
        v=copy.deepcopy(self.s.snapshot(self.host)['vehicles'][0]);v['graphic']='missing'
        with self.assertRaises(ValueError):self.s.command(self.host,'vehicle',v)
    def test_clock_stops_when_all_players_are_offline(self):
        self.s.command(self.host,'control',{'paused':False});before=self.s.snapshot(self.host)['clock'];self.s.tick(1);self.assertGreater(self.s.snapshot(self.host)['clock'],before)
        self.s.command(self.host,'leave',{});self.s.command(self.guest,'leave',{});before=self.s.snapshot(self.host)['clock'];self.s.tick(10);self.assertEqual(self.s.snapshot(self.host)['clock'],before)

class MigrationTest(unittest.TestCase):
    def test_adopt_v01_preserves_custom_fleet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'db');db=sqlite3.connect(path);db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY,value TEXT NOT NULL)');state=seed();state['vehicles'][0]['callsign']='CUSTOM';db.execute('INSERT INTO state VALUES (1,?)',(json.dumps(state),));db.commit();db.close()
            s=Sessions(path);credential=s.create({'name':'Julian','adopt_legacy':True});member=s.member(credential['token']);self.assertEqual(s.snapshot(member)['vehicles'][0]['callsign'],'CUSTOM');s.close()
if __name__=='__main__':unittest.main()
