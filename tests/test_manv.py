import copy
import unittest
from unittest.mock import patch
import test_fleet as helpers
from manv_scenarios import MANV_SCENARIOS
from multiple_patients import triage

class ManvTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def incident(self,scores=None):
        scenario=copy.deepcopy(MANV_SCENARIOS[0])
        if scores is not None:scenario['_scenario'].update(patient_count=len(scores),patient_scores=scores)
        j=self.e.new_job('emergency',manual=True,scenario=scenario);j['accepted']=True
        return j

    def arrive(self,j,call,assess=True):
        v=self.vehicle(call);self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v);self.e.advance(v)
        if assess:
            self.e.state['clock']=v['assessment_due']
            with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}):self.e.update_assessments(self.e.state['clock'])
        return v

    def test_four_scenarios_hidden_until_assessment(self):
        self.assertEqual(sorted(s['_scenario']['patient_count'] for s in MANV_SCENARIOS),[6,8,10,12])
        j=self.incident();v=self.arrive(j,'77/002',False)
        visible=next(x for x in self.e.snapshot()['jobs'] if x['id']==j['id'])
        self.assertNotIn('patients',visible);self.assertNotIn('manv',visible)
        self.e.state['clock']=v['assessment_due'];self.e.update_assessments(self.e.state['clock'])
        self.assertEqual(len(j['patients']),6);self.assertTrue(j['manv'])
        self.assertEqual(j['patients'][v['patient_index']]['percent'],18)
        self.assertEqual([triage(n) for n in (0,44,45,69,70,100)],['I','I','II','II','III','III'])

    def test_doctor_treats_worst_and_switches_dynamically(self):
        j=self.incident([10,12,80]);self.arrive(j,'77/002');nef=self.arrive(j,'77/099')
        self.e.assign_doctors(j);self.assertEqual(nef['treating_patient'],1)
        self.e.state['clock']=max(self.e.state['clock'],j['patients_next_change'])+60
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}),patch('multiple_patients.random.randint',side_effect=lambda a,b:4 if a==4 else 0):self.e.update_patients(self.e.state['clock'])
        self.assertTrue(all(p['percent']>before for p,before in zip(j['patients'],[10,12,80])))
        self.assertEqual(nef['treating_patient'],2)

    def test_nef_and_nah_equal_care_without_double_treatment(self):
        j=self.incident([15,25,80]);self.arrive(j,'77/002');nef=self.arrive(j,'77/099');nah=self.arrive(j,'C3')
        self.e.assign_doctors(j);self.assertEqual({nef['treating_patient'],nah['treating_patient']},{1,2})
        self.e.state['clock']=max(self.e.state['clock'],j['patients_next_change'])+60
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}),patch('multiple_patients.random.randint',side_effect=lambda a,b:6 if a==4 else 0):self.e.update_patients(self.e.state['clock'])
        self.assertTrue(all(p['percent']>before for p,before in zip(j['patients'],[15,25,80])))
        self.assertIsNone(j['patients'][2]['doctor'])

    def test_nef_can_request_both_transport_and_notarzt(self):
        j=self.incident([10,20,30,35,38,40,70,80]);self.arrive(j,'77/002');nef=self.arrive(j,'77/099')
        self.e.state['radio_calls']=[]
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'1'}):
            self.e.request_manv_resources(j,nef);self.e.request_manv_resources(j,nef)
        self.assertCountEqual([c['kind'] for c in self.e.state['radio_calls']],['NEF','RTW'])
        self.assertTrue(all(c['vehicle']==nef['id'] for c in self.e.state['radio_calls']))
        self.assertIn('7 transportierende',next(c for c in self.e.state['radio_calls'] if c['kind']=='RTW')['reason'])

    def test_unassessed_doctor_waits_and_nef_cannot_transport(self):
        j=self.incident([10,80]);self.arrive(j,'77/002');nef=self.arrive(j,'77/099',False)
        self.e.assign_doctors(j);self.assertTrue(all(p.get('doctor') is None for p in j['patients']))
        with self.assertRaises(ValueError):self.e.start_transport(nef)
        nef.pop('assessment_due');self.e.assign_doctors(j)
        self.e.advance(nef);self.assertEqual(nef['status'],'scene');self.assertIsNotNone(nef['phase_due'])

    def test_nef_escort_is_not_a_second_patient_and_returns_after_three_minutes(self):
        j=self.incident([20,80]);rtw=self.arrive(j,'77/002');nef=self.arrive(j,'77/099')
        self.e.assign_doctors(j);j.update(destination='kh-hainburg',bed_state='crew_selected')
        self.e.start_transport(rtw)
        self.assertEqual(nef['status'],'transport');self.assertEqual(nef['escort_of'],rtw['id']);self.assertNotIn('patient_index',nef)
        self.assertEqual(self.e.missing_carriers(j),1)
        self.e.advance(nef);self.assertEqual(nef['status'],'hospital');self.assertEqual(nef['phase_due']-self.e.state['clock'],180)
        self.e.state['clock']=nef['phase_due'];self.e.advance(nef)
        self.assertEqual(nef['status'],'radio');self.assertIsNone(nef['job']);self.assertFalse(any(p['delivered'] for p in j['patients']))
        self.e.advance(rtw);self.assertEqual(rtw['phase_due']-self.e.state['clock'],180)
        self.e.state['clock']=rtw['phase_due'];self.e.advance(rtw)
        self.assertEqual(rtw['status'],'radio');self.assertTrue(j['patients'][0]['delivered']);self.assertFalse(j['patient_delivered'])
        self.e.advance(rtw);self.assertEqual(rtw['status'],'ready')

    def test_remaining_patients_evolve_while_first_is_in_transport(self):
        j=self.incident([20,30,80]);first=self.arrive(j,'77/002');nef=self.arrive(j,'77/099');second=self.arrive(j,'77/004')
        self.e.assign_doctors(j);j.update(destination='kh-hainburg',bed_state='crew_selected');self.e.start_transport(first)
        self.assertEqual(second['status'],'scene')
        before=j['patients'][1]['percent'];self.e.state['clock']=max(self.e.state['clock'],j['patients_next_change'])+60
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}),patch('multiple_patients.random.randint',side_effect=lambda a,b:4 if a==4 else -2):self.e.update_patients(self.e.state['clock'])
        self.assertLess(j['patients'][1]['percent'],before);self.assertEqual(j['patients'][0]['percent'],24)

    def test_aaos_consider_all_patients_and_doctor_shortage(self):
        j=self.incident([10,20,30,80]);self.arrive(j,'77/002')
        result=self.e.recommendation(j);units=[self.e.get('vehicles',id) for id in result['vehicles']]
        self.assertEqual(sum(v['type'] in ('RTW','RTW-C','KTW') for v in units),3)
        self.assertEqual(sum(v['type'] in ('NEF','NAH') for v in units),1)
        self.assertEqual(len(set(result['vehicles'])),len(result['vehicles']))

    def test_handover_target_is_frozen_and_patient_state_persists(self):
        j=self.incident([70,80]);v=self.arrive(j,'77/002');j.update(destination='kh-hainburg',bed_state='crew_selected');self.e.start_transport(v)
        j['destination']='kh-baden';self.e.advance(v)
        self.assertEqual((v['lat'],v['lon']),(self.e.get('hospitals','kh-hainburg')['lat'],self.e.get('hospitals','kh-hainburg')['lon']))
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);saved=self.e.get('jobs',j['id']);self.assertEqual(saved['patients'],j['patients'])

    def test_one_c9_covers_six_patients_without_nef_per_critical_patient(self):
        j=self.incident();self.arrive(j,'77/002');nah=self.arrive(j,'C9')
        self.e.state['radio_calls']=[];before=[p['percent'] for p in j['patients']]
        self.e.state['clock']=max(self.e.state['clock'],j['patients_next_change'])+60
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'1'}),patch('multiple_patients.random.randint',return_value=-4):self.e.update_patients(self.e.state['clock'])
        self.assertTrue(all(p['percent']>=value for p,value in zip(j['patients'],before)))
        self.assertTrue(all(p['percent']>value for p,value in zip(j['patients'],before)))
        self.assertFalse(any(c['kind']=='NEF' for c in self.e.state['radio_calls']))
        self.assertEqual(self.e.doctor_demand(j),1)

    def test_more_doctors_improve_all_patient_states_faster(self):
        j=self.incident();self.arrive(j,'77/002');self.arrive(j,'77/099')
        baseline=[p['percent'] for p in j['patients']]
        self.e.state['clock']=max(self.e.state['clock'],j['patients_next_change'])+60
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}):self.e.update_patients(self.e.state['clock'])
        one=[p['percent']-value for p,value in zip(j['patients'],baseline)]
        self.arrive(j,'C3')
        for p,value in zip(j['patients'],baseline):p['percent']=value
        self.e.state['clock']=max(self.e.state['clock'],j['patients_next_change'])+60
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}):self.e.update_patients(self.e.state['clock'])
        two=[p['percent']-value for p,value in zip(j['patients'],baseline)]
        self.assertTrue(all(faster>slower for faster,slower in zip(two,one)))

    def test_arrived_doctor_already_prevents_decline_during_assessment(self):
        j=self.incident();self.arrive(j,'77/002');self.arrive(j,'77/099',False)
        before=[p['percent'] for p in j['patients']];j['patients_next_change']=self.e.state['clock']
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'0'}),patch('multiple_patients.random.randint',return_value=-4):self.e.update_patients(self.e.state['clock'])
        self.assertEqual([p['percent'] for p in j['patients']],before)

    def test_negative_closes_request_and_suppresses_repeated_demand(self):
        j=self.incident([20,80]);v=self.arrive(j,'77/002')
        c=self.e.raise_radio(j,v,'NEF',reason_initial=True)
        for step in ('listen','unavailable'):self.e.command('radio',{'job':j['id'],'call':c['id'],'step':step})
        self.assertEqual(c['state'],'closed');self.assertTrue(c['declined'])
        self.assertIsNone(self.e.raise_radio(j,v,'NEF'))
        self.e.crew_destination(v);self.assertEqual(v['status'],'transport')
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);j=self.e.get('jobs',j['id'])
        self.assertIn('NEF',j['request_denials'])
        self.e.command('radio_retry',{'job':j['id'],'kind':'NEF'});self.assertNotIn('NEF',j['request_denials'])
