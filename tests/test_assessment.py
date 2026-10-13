import unittest
from unittest.mock import patch
import test_fleet as helpers

class AssessmentTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def arrive(self):
        j=self.job();v=self.vehicle('77/002')
        self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v)
        with patch('operations.random.randint',return_value=90):self.e.advance(v)
        return j,v

    def test_arrival_reports_status_but_waits_for_assessment(self):
        j,v=self.arrive();due=v['assessment_due']
        self.assertEqual(v['status'],'scene');self.assertFalse(j['patient_condition']['reported'])
        self.assertFalse(any(l['channel']=='Funk' for l in self.e.state['logs']))
        self.e.update_assessments(due-1);self.assertFalse(j['patient_condition']['reported'])
        with self.assertRaises(ValueError):self.e.raise_radio(j,v,'NEF')
        self.e.state['clock']=due;self.e.update_assessments(due)
        self.assertTrue(j['patient_condition']['reported'])
        before=len(self.e.state['logs']);self.e.update_assessments(due+1)
        self.assertEqual(before,len(self.e.state['logs']))

    def test_pause_keeps_assessment_pending_and_reload_preserves_due(self):
        j,v=self.arrive();due=v['assessment_due'];self.e.state['paused']=True
        self.e.tick(120);self.assertFalse(j['patient_condition']['reported'])
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        self.assertEqual(self.e.get('vehicles',v['id'])['assessment_due'],due)

    def test_no_report_after_resource_leaves_scene(self):
        j,v=self.arrive();due=v['assessment_due'];v['status']='radio';v['job']=None
        self.e.update_assessments(due);self.assertFalse(j['patient_condition']['reported'])
