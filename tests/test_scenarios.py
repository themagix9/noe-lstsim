import unittest
from unittest.mock import patch
import test_fleet as helpers
from scenarios import EXTRA_SCENARIOS

class ScenarioTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle

    def incident(self,id):
        scenario=next(s for s in EXTRA_SCENARIOS if s['scenario_id']==id)
        j=self.e.new_job('emergency',scenario=scenario);j['accepted']=True
        return j

    def arrive(self,j):
        v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        self.e.depart(v);self.e.state['clock']=v['phase_due'];self.e.advance(v)
        return v

    def assess(self,v):
        self.e.state['clock']=v['assessment_due'];self.e.update_assessments(self.e.state['clock'])

    def test_truth_hidden_until_assessment_and_code_does_not_rewrite_it(self):
        j=self.incident('seizure-mistaken-stroke')
        self.e.edit_job({'job':j['id'],'code':'RD-28C1L'})
        self.assertEqual(j['patient_condition']['percent'],38)
        visible=next(x for x in self.e.snapshot()['jobs'] if x['id']==j['id'])
        self.assertNotIn('_scenario',visible);self.assertNotIn('scene',visible)
        self.assertNotIn('percent',visible['patient_condition'])
        v=self.arrive(j);self.assertNotIn('scene_report',j)
        self.e.update_assessments(v['assessment_due']-1);self.assertNotIn('scene_report',j)
        self.assess(v);self.assertIn('Krampfanfall',j['scene_report']['text'])
        self.assertTrue(j['patient_condition']['reported'])
        self.assertEqual(j['code'],'RD-28C1L')

    def test_false_alarm_has_no_phantom_patient_transport_or_doctor(self):
        j=self.incident('garage-smoke');v=self.arrive(j)
        self.assertIsNone(j['patient_condition']);self.assertFalse(j.get('no_patient'))
        self.assess(v);self.assertTrue(j['no_patient']);self.assertIsNone(j['patient'])
        self.assertFalse(self.e.state['radio_calls']);self.assertIsNone(j['destination'])
        with self.assertRaises(ValueError):self.e.start_transport(v)
        self.e.state['clock']=v['phase_due'];self.e.advance(v)
        self.assertEqual(j['status'],'done');self.assertIsNone(v['job']);self.assertEqual(v['status'],'radio')
        self.assertFalse(any('Status 4' in l['text'] for l in self.e.state['logs']))

    def test_fire_standby_holds_and_survives_reload(self):
        j=self.incident('fire-standby');v=self.arrive(j);self.assess(v)
        self.assertAlmostEqual(v['phase_due']-self.e.state['clock'],600,places=6)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);saved=self.e.get('jobs',j['id'])
        self.assertEqual(saved['scene_report'],j['scene_report']);self.assertIsNone(saved['patient_condition'])
        self.assertEqual(saved['_scenario']['hold_seconds'],600)

    def test_fire_call_and_scenario_specific_answers(self):
        j=self.incident('garage-smoke');self.e.accept_call(j)
        self.assertIn('Feuerwehr',j['call']['transcript'][1]['text'])
        for q in j['call']['questions']:self.e.question_call({'job':j['id'],'question':q['key']})
        self.assertEqual(j['call']['state'],'ready')
        patient=next(q for q in j['call']['questions'] if q['key']=='patient')
        self.assertIn('keine verletzten',patient['answer'])
        self.assertNotIn(j['_scenario']['report'],str(j['call']['transcript']))

    def test_scenario_decline_then_doctor_support(self):
        j=self.incident('fall-underestimated');v=self.arrive(j);self.assess(v)
        j['patient_condition']['next_change']=self.e.state['clock']
        before=j['patient_condition']['percent']
        with patch('patients.random.randint',return_value=-8):self.e.update_patients(self.e.state['clock'])
        self.assertEqual(j['patient_condition']['percent'],before-8)
        self.assertTrue(j['patient_condition']['notarzt_required'])

    def test_wrong_cpr_code_does_not_create_cardiac_arrest(self):
        j=self.incident('fall-underestimated');self.e.edit_job({'job':j['id'],'code':'RD-9E1'})
        self.assertEqual(j['patient_condition']['percent'],40)
        self.e.ecpr_precall(j);self.assertFalse(j['exercise_cpr'])
