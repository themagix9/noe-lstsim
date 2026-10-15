import unittest
import test_fleet as helpers

class RadioFrequencyTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def scene(self,kind='emergency'):
        j=self.job(kind);v=self.vehicle('77/002');j.update(vehicles=[v['id']],routine_radio_roll=.8)
        v.update(job=j['id'],status='scene',assessment_due=0)
        self.e.ensure_patient_condition(j);j['patient_condition'].update(percent=95,notarzt_required=False,reported=False)
        self.e.state['logs']=[];self.e.state['radio_calls']=[]
        return j,v

    def test_transport_pickup_is_status_not_routine_radio(self):
        j,v=self.scene('transport');self.e.patient_report(j,v);self.assertTrue(j['patient_condition']['reported'])
        self.assertEqual(self.e.state['radio_calls'],[]);self.e.crew_destination(v)
        self.assertEqual(v['status'],'transport')
        self.assertFalse(any(l['channel']=='Funk' for l in self.e.state['logs']))
        self.assertTrue(any(l['channel']=='Status' and 'Status 4' in l['text'] for l in self.e.state['logs']))

    def test_code_levels_and_rare_kt_use_one_persistent_decision(self):
        j,v=self.scene();j['routine_radio_roll']=.2
        for code,expected in [('RD-1A1',False),('RD-1B1',True),('RD-1C1',True),('RD-1D1',True),('RD-9E1',True)]:
            j['code']=code;self.assertEqual(self.e.routine_radio_enabled(j),expected)
        j['kind']='transport';self.assertFalse(self.e.routine_radio_enabled(j));j['routine_radio_roll']=.01
        self.assertTrue(self.e.routine_radio_enabled(j));self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);j=self.e.get('jobs',j['id']);self.assertTrue(self.e.routine_radio_enabled(j))
        self.assertNotIn('routine_radio_roll',self.e.snapshot()['jobs'][-1])

    def test_second_resource_overrides_quiet_low_code_and_explicit_radio_remains_possible(self):
        j,v=self.scene();j.update(code='RD-1A1',routine_radio_roll=.99)
        self.e.patient_report(j,v);self.assertEqual(self.e.state['radio_calls'],[])
        other=self.vehicle('77/011');other.update(job=j['id'],status='scene',assessment_due=0);j['vehicles'].append(other['id'])
        self.e.patient_report(j,other);self.assertTrue(self.e.state['radio_calls'])
        self.assertTrue(self.e.routine_radio_enabled(j))
        self.e.state['radio_calls']=[];j,v=self.scene('transport')
        self.e.raise_scene_radio(j,v,force=True);self.assertEqual(self.e.state['radio_calls'][-1]['kind'],'Lagemeldung')

    def test_quiet_rd_still_sets_destination_and_wiener_request_is_never_suppressed(self):
        j,v=self.scene();j.update(code='RD-1A1',routine_radio_roll=.99,crew_target='kh-hainburg')
        self.e.crew_destination(v);self.assertEqual(v['status'],'transport');self.assertEqual(j['destination'],'kh-hainburg')
        self.assertFalse(any(l['channel']=='Funk' for l in self.e.state['logs']))
        j,v=self.scene();j.update(code='RD-1A1',routine_radio_roll=.99,crew_target='kh-donaustadt')
        self.e.crew_destination(v);self.assertEqual(j['bed_state'],'requested')
        self.assertTrue(any(l['channel']=='Funk' and 'benötigen ein Ziel in Wien' in l['text'] for l in self.e.state['logs']))
