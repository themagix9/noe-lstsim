import json
import unittest
from unittest.mock import patch
import test_fleet as helpers
from hospitals import DIRECTORY,nearby,plan_transport,destination
from scenario_catalog import CATALOG

class ExpansionTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def test_catalog_codes_and_real_placements(self):
        self.assertEqual(len(CATALOG),52)
        for source in CATALOG:
            self.assertIsNotNone(self.e.rule(source['suggested_code']))
            j=self.e.new_job('emergency',scenario=source)
            self.assertEqual(j['address'],j['address_point']['address'])
            self.assertNotIn('_scenario',self.e.snapshot()['jobs'][-1])

    def test_country_directory_sites_regions_and_no_duplicate_ids(self):
        hospitals=self.e.state['hospitals'];self.assertGreaterEqual(len(hospitals),304)
        self.assertEqual(len({h['id']for h in hospitals}),len(hospitals))
        self.assertEqual(len({h['region']for h in hospitals}),9)
        self.assertTrue(all(h.get('address')for h in hospitals))
        choices=nearby(self.e,{'lat':48.14,'lon':16.48},emergency=True)
        self.assertTrue(all(h.get('emergency',True)for h in choices))
        self.assertLess(choices[0]['lat'],49)
        self.assertEqual(DIRECTORY['institution_count'],254)

    def test_both_transport_directions_and_home_delivery(self):
        for route in ('noe-to-vienna','vienna-to-noe','hospital-transfer'):
            j=self.job('transport')
            def choice(items):return route if route in items else items[0]
            with patch('random.choice',side_effect=choice):plan_transport(self.e,j)
            target=destination(self.e,j)
            self.assertTrue(target.get('address'))
            if route=='noe-to-vienna':self.assertEqual(target['region'],'Wien')
            else:self.assertEqual(self.e.get('hospitals',j['origin_hospital'])['region'],'Wien');self.assertEqual(target['region'],'NÖ')
            v=self.vehicle('77/003');v.update(job=j['id'],status='scene');j['vehicles']=[v['id']]
            self.e.start_transport(v);self.assertEqual(v['status'],'transport')
            self.assertEqual(v['leg']['target_lat'],target['lat'])
            self.e.advance(v);self.assertEqual(v['status'],'hospital');self.e.advance(v);self.assertEqual(j['status'],'done')

    def fuel(self):
        v=self.vehicle('77/002');v.update(status='radio',phase_due=None,leg=None)
        c=self.e.request_fuel(v);self.e.command('fuel_radio',{'call':c['id'],'step':'listen'});return v,c

    def test_fuel_approval_blocks_dispatch_for_five_minutes(self):
        v,c=self.fuel();self.e.command('fuel_radio',{'call':c['id'],'step':'allow'})
        self.assertEqual(v['status'],'duty');self.assertFalse(self.e.sendable(v,self.job()))
        due=v['phase_due'];self.e.update_fuel(due-1);self.assertEqual(v['status'],'duty')
        self.e.update_fuel(due);self.assertEqual(v['status'],'radio');self.assertFalse(v['fueling'])

    def test_denied_fuel_remains_available_and_conversation_ends(self):
        v,c=self.fuel();self.e.command('fuel_radio',{'call':c['id'],'step':'deny'})
        self.assertEqual(v['status'],'radio');self.assertEqual(c['state'],'closed');self.assertTrue(self.e.sendable(v,self.job()))
        self.assertTrue(any(l['text']=='LEO Ende.'for l in self.e.state['logs']))

    def test_fuel_request_cannot_take_busy_or_fr_unit(self):
        with self.assertRaises(ValueError):self.e.request_fuel(self.vehicle('77/002'))
        with self.assertRaises(ValueError):self.e.request_fuel(self.vehicle('FR-SCH-01'))
        v,c=self.fuel();j=self.job();self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        with self.assertRaises(ValueError):self.e.command('fuel_radio',{'call':c['id'],'step':'allow'})

    def test_two_patients_request_and_complete_separate_transports(self):
        source=next(s for s in CATALOG if s['scenario_id']=='two-crash');j=self.e.new_job('emergency',scenario=source);j['accepted']=True
        first=self.vehicle('77/002');second=self.vehicle('77/004')
        self.e.dispatch({'job':j['id'],'vehicles':[first['id']]});self.e.depart(first);self.e.advance(first)
        self.e.state['clock']=first['assessment_due']
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'1'}):self.e.update_assessments(self.e.state['clock'])
        self.assertEqual(j['patient_count'],2);self.assertEqual(self.e.missing_carriers(j),1)
        request=next(c for c in self.e.state['radio_calls'] if c['kind']=='RTW');self.e.command('radio',{'job':j['id'],'call':request['id'],'step':'listen'})
        self.e.dispatch({'job':j['id'],'vehicles':[second['id']]});self.e.command('radio',{'job':j['id'],'call':request['id'],'step':'confirm'})
        self.e.depart(second);self.e.advance(second);self.assertEqual(self.e.missing_carriers(j),0)
        self.e.crew_destination(first);self.assertEqual(first['status'],'transport');self.assertEqual(second['job'],j['id'])
        self.e.advance(first);self.e.advance(first);self.assertFalse(j['patient_delivered']);self.assertNotEqual(j['status'],'done')
        self.e.crew_destination(second);self.e.advance(second);self.e.advance(second)
        self.assertTrue(j['patient_delivered']);self.assertEqual(j['status'],'done');self.assertTrue(all(p['delivered']for p in j['patients']))

    def test_storno_is_per_unit_and_sends_both_channels(self):
        j=self.job();first=self.vehicle('77/002');second=self.vehicle('77/004')
        self.e.dispatch({'job':j['id'],'vehicles':[first['id'],second['id']]});self.e.depart(second)
        self.e.command('resource_call',{'job':j['id'],'vehicle':second['id']});c=self.e.state['radio_calls'][-1]
        with self.assertRaises(ValueError):self.e.command('cancel_radio',{'job':j['id'],'call':c['id'],'step':'cancel'})
        self.e.command('cancel_radio',{'job':j['id'],'call':c['id'],'step':'answer'})
        self.e.command('cancel_radio',{'job':j['id'],'call':c['id'],'step':'cancel'})
        self.assertIsNone(second['job']);self.assertEqual(first['job'],j['id']);self.assertNotIn(second['id'],j['vehicles'])
        messages=[m for m in self.e.state['messages'] if m['text'].startswith('EINSATZSTORNO')]
        self.assertEqual({m['channel'] for m in messages},{'SDS','ESApp'});self.assertEqual(c['state'],'closed')

    def test_storno_protects_patient_in_transport_and_other_owner(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        j['owner']='one'
        with self.assertRaises(ValueError):self.e.command('resource_call',{'job':j['id'],'vehicle':v['id'],'_actor':{'id':'two'}})
        v['status']='transport'
        with self.assertRaises(ValueError):self.e.contact_resource({'job':j['id'],'vehicle':v['id']})
