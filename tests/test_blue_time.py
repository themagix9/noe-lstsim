import unittest
import test_fleet as helpers
from aao import estimated_seconds

class BlueTimeTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def prepare(self):
        j=self.job();v=self.vehicle('77/002');v['job']=j['id'];v['turnout']=60
        class Roads:
            enabled=True
            url='http://test-osrm'
            def route(self,*args):return {'status':'ready','seconds':600,'distance_m':10000,'geometry':[[48,16],[48.1,16.1]],'cumulative':[0,10000]}
            def cached_eta(self,*args):return {'status':'ready','seconds':600}
            def estimates(self,origins,target):return {v['id']:{'status':'ready','seconds':600,'distance_m':10000} for v in origins}
        self.e.router=Roads();return j,v

    def test_route_and_aao_apply_factor_to_travel_only(self):
        j,v=self.prepare();j['signal']=False;now=self.e.state['clock']
        self.e.drive(v,j,'enroute');self.assertEqual(v['phase_due']-now,600)
        self.assertEqual(estimated_seconds(self.e,v,j),660)
        j['signal']=True;self.e.drive(v,j,'enroute')
        self.assertEqual(v['phase_due']-now,510)
        self.assertEqual(estimated_seconds(self.e,v,j),570)
        self.e.drive(v,j,'transport');self.assertEqual(v['phase_due']-now,510)
        self.e.drive(v,j,'radio');self.assertEqual(v['phase_due']-now,600)

    def test_setting_validates_and_does_not_retime_active_leg(self):
        j,v=self.prepare();j['signal']=True;self.e.drive(v,j,'enroute');due=v['phase_due']
        self.e.command('travel_settings',{'blue_light_factor':.75})
        self.assertEqual(v['phase_due'],due)
        self.e.drive(v,j,'enroute');self.assertEqual(v['phase_due']-self.e.state['clock'],450)
        for invalid in (0,1.1,'bad',float('nan')):
            with self.assertRaises(ValueError):self.e.command('travel_settings',{'blue_light_factor':invalid})
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertEqual(self.e.state['setup']['blue_light_factor'],.75)

    def test_helicopters_and_first_responders_have_no_blue_speed_bonus(self):
        j,v=self.prepare();j['signal']=True
        for kind in ('NAH','FR'):
            v['type']=kind;self.assertEqual(self.e.response_factor(v,j),1)
