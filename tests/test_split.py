import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from sessions import Sessions

class SplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=str(Path(self.tmp.name)/'db');self.s=Sessions(self.path)
        auth=self.s.create({'name':'Dispo','mode':'multi','workflow':'split','role':'dispatcher'})
        self.dispo=self.s.member(auth['token']);self.code=self.s.snapshot(self.dispo)['session']['code']
        ct=self.s.join({'name':'Calltaker','code':self.code,'role':'calltaker'});self.ct=self.s.member(ct['token'])
        self.e=self.s.engine(self.ct['room_id']);self.s.command(self.dispo,'generate',{'kind':'emergency'});self.j=self.e.state['jobs'][-1]
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def ask(self):
        self.s.command(self.ct,'accept',{'id':self.j['id']})
        for q in self.j['call']['questions']:self.s.command(self.ct,'call_question',{'job':self.j['id'],'question':q['key']})
    def test_roles_and_draft_are_enforced_on_server(self):
        self.assertEqual(self.s.snapshot(self.ct)['session']['role'],'calltaker')
        with self.assertRaises(PermissionError):self.s.command(self.dispo,'accept',{'id':self.j['id']})
        with self.assertRaises(PermissionError):self.s.command(self.dispo,'claim',{'id':self.j['id']})
        with self.assertRaises(PermissionError):self.s.command(self.ct,'dispatch',{'job':self.j['id'],'vehicles':[]})
        self.s.command(self.ct,'accept',{'id':self.j['id']})
        with self.assertRaises(ValueError):self.s.command(self.ct,'handoff',{'job':self.j['id']})
    def test_support_is_dispatcher_only_after_handoff(self):
        v=next(v for v in self.e.state['vehicles'] if v['callsign']=='C15')
        data={'job':self.j['id'],'vehicle':v['id']}
        with self.assertRaises(PermissionError):self.s.command(self.ct,'support_request',data)
        with self.assertRaises(PermissionError):self.s.command(self.dispo,'support_request',data)
        self.ask()
        self.s.command(self.ct,'edit_job',{'job':self.j['id'],'code':'RD-17B1'})
        self.s.command(self.ct,'handoff',{'job':self.j['id']})
        self.s.command(self.dispo,'support_request',data)
        self.assertEqual(self.j['support_requests'][0]['state'],'pending')
        with self.assertRaises(PermissionError):self.s.command(self.ct,'support_cancel',{'job':self.j['id'],'request':self.j['support_requests'][0]['id']})
    def test_live_transcript_handoff_and_dispatch(self):
        self.ask();self.assertEqual(len(self.s.snapshot(self.dispo)['jobs'][-1]['call']['transcript']),14)
        self.s.command(self.ct,'handoff',{'job':self.j['id'],'note':'Zugang über Hintereingang.'})
        self.assertIsNone(self.j['owner']);self.assertEqual(self.j['call']['state'],'ended')
        self.assertEqual(self.j['handoff']['note'],'Zugang über Hintereingang.')
        self.s.command(self.dispo,'claim',{'id':self.j['id']})
        self.s.command(self.dispo,'edit_job',{'job':self.j['id'],'code':'RD-17B1'})
        v=next(v for v in self.e.state['vehicles'] if v['callsign']=='77/002')
        self.s.command(self.dispo,'dispatch',{'job':self.j['id'],'vehicles':[v['id']]})
        self.assertEqual(v['job'],self.j['id']);self.assertEqual(self.j['owner'],self.dispo['id'])
        with self.assertRaises(PermissionError):self.s.command(self.ct,'edit_job',{'job':self.j['id'],'code':'RD-17B1'})
    def test_roles_and_handoff_survive_reload(self):
        self.ask();self.s.command(self.ct,'handoff',{'job':self.j['id'],'note':'Notiz'});self.s.close();self.s=Sessions(self.path)
        member=self.s.db.execute('SELECT role FROM members WHERE id=?',(self.ct['id'],)).fetchone();self.assertEqual(member[0],'calltaker')
        self.assertEqual(self.s.engine(self.ct['room_id']).get('jobs',self.j['id'])['handoff']['note'],'Notiz')
    def test_split_increases_call_rate(self):
        now=self.e.state['clock'];self.e.state.update(paused=False,next_emergency=now,next_transport=now+9999)
        with patch('engine.random.randint',return_value=1000):self.e.tick(1)
        self.assertEqual(self.e.state['next_emergency']-self.e.state['clock'],500)

    def test_signal_controls_follow_split_role_and_handoff(self):
        data={'job':self.j['id'],'vehicle':'not-yet-dispatched','signal':True}
        for action in ('signal_contact','signal_radio'):
            with self.assertRaises(PermissionError):self.s.command(self.ct,action,data)
        with self.assertRaises(PermissionError):self.s.command(self.dispo,'job_signal',data)
        self.ask();self.s.command(self.ct,'job_signal',{'job':self.j['id'],'signal':False})
        self.assertFalse(self.j['signal'])
        self.s.command(self.ct,'handoff',{'job':self.j['id']})
        with self.assertRaises(PermissionError):self.s.command(self.ct,'job_signal',data)

    def test_retrying_automatic_requests_is_dispatcher_only(self):
        with self.assertRaises(PermissionError):self.s.command(self.ct,'radio_retry',{'job':self.j['id'],'kind':'NEF'})
