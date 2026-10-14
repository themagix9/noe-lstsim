import unittest
from unittest.mock import patch
import test_fleet as helpers
from turnout import seconds, preparation
from aao import estimated_seconds

class TurnoutTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def test_day_night_caps_and_urgency(self):
        v=self.vehicle('77/001');j=self.job()
        for clock,cap in ((6*3600,120),(18*3600,180),(5*3600,180)):
            self.e.state['clock']=clock
            durations=[]
            for level in 'ABCDE':
                j['code']='RD-9'+level+'1'
                duration=seconds(self.e,v,j);durations.append(duration)
                self.assertGreater(duration,0);self.assertLessEqual(duration,cap)
                self.assertEqual(seconds(self.e,v,j),duration)
            self.assertEqual(durations,sorted(durations,reverse=True))
            j['code']='RD-9E1';self.assertTrue(15<=seconds(self.e,v,j)<=25)

    def test_actual_departure_matches_eta_for_ack_and_direct(self):
        for direct in (False,True):
            with self.subTest(direct=direct):
                v=self.vehicle('77/001');v.update(status='ready',job=None,leg=None)
                self.e.state['clock']=8*3600;j=self.job();j['code']='RD-9E1'
                delay=seconds(self.e,v,j);start=self.e.state['clock']
                with patch('operations.random.random',return_value=.1 if direct else .9):
                    self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
                self.assertEqual(v['turnout_due'],start+delay)
                while self.e.state['clock']<start+delay:
                    self.assertIn(v['status'],('assigned','acknowledged'))
                    self.assertIsNone(v['leg'])
                    self.e.state['clock']+=1
                    if self.e.state['clock']>=v['phase_due']:self.e.advance(v)
                self.assertEqual(v['status'],'enroute')
                self.assertEqual(v['leg']['start'],start+delay)

    def test_eta_includes_same_preparation_and_handover(self):
        v=self.vehicle('77/002');j=self.job();j['code']='RD-9E1'
        class Roads:
            enabled=True
            url='http://test-osrm'
            def cached_eta(self,*args):return {'status':'ready','seconds':600}
            def estimates(self,origins,target):return {x['id']:{'status':'ready','seconds':600,'distance_m':10000} for x in origins}
        self.e.router=Roads();j['signal']=True
        expected=600*.85+preparation(self.e,v,j)
        self.assertEqual(estimated_seconds(self.e,v,j),expected)
        eta=next(x for x in self.e.snapshot()['jobs'] if x['id']==j['id'])['resource_eta'][v['id']]
        self.assertEqual(eta['seconds'],expected)
        self.assertEqual(eta['turnout_seconds'],seconds(self.e,v,j))
        v.update(status='hospital',phase_due=self.e.state['clock']+200)
        self.assertEqual(preparation(self.e,v,j),200+seconds(self.e,v,j))

    def test_radio_and_aircraft_preparation(self):
        v=self.vehicle('77/002');j=self.job();j['code']='RD-9A1'
        v['status']='radio';self.assertTrue(5<=seconds(self.e,v,j)<=15)
        v.update(type='NAH',turnout=180,status='ready')
        j['code']='RD-9E1';self.assertEqual(seconds(self.e,v,j),180)

    def test_quittierung_does_not_restart_turnout_and_reload_preserves_due(self):
        v=self.vehicle('77/001');j=self.job();j['code']='RD-9E1'
        self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});due=v['turnout_due']
        self.e.acknowledge(v);self.assertEqual(v['phase_due'],due)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);v=self.e.get('vehicles',v['id'])
        self.assertEqual(v['turnout_due'],due)
        self.e.command('reset',{});self.assertIsNone(self.e.get('vehicles',v['id'])['turnout_due'])

    def test_fast_forward_keeps_exact_alarm_departure_time(self):
        v=self.vehicle('77/001');j=self.job();j['code']='RD-9E1'
        start=self.e.state['clock'];delay=seconds(self.e,v,j)
        with patch('operations.random.random',return_value=.9):
            self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        self.e.state.update(paused=False,speed=60)
        self.e.tick(1)
        self.assertEqual(v['status'],'enroute')
        self.assertEqual(v['leg']['start'],start+delay)
        self.assertEqual(self.e.state['clock'],start+60)
