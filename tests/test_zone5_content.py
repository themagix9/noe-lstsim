import unittest
from unittest.mock import patch
import test_fleet as helpers
from locations import ADDRESS_CITIES,choose_address
from scenario_catalog import CATALOG
from scenario_zone5 import SCENARIOS,choose

class ZoneContentTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown

    def test_original_codes_unique_observations_and_false_alarm_truth(self):
        self.assertGreaterEqual(len(SCENARIOS),138)
        self.assertEqual(len({s['scenario_id'] for s in CATALOG}),len(CATALOG))
        self.assertEqual(len({s['caller'] for s in SCENARIOS}),len(SCENARIOS))
        self.assertGreaterEqual(sum(s['_scenario']['no_patient'] for s in SCENARIOS),20)
        for source in SCENARIOS:
            self.assertIsNotNone(self.e.rule(source['suggested_code']))
            self.assertNotEqual(source['caller'],source['_scenario']['report'])
        false=next(s for s in SCENARIOS if s['scenario_id']=='zone5-false-00')
        j=self.e.new_job('emergency',scenario=false)
        self.assertFalse(j.get('no_patient'));self.assertIsNone(j['patient_condition'])
        snapshot=self.e.snapshot()['jobs'][-1];self.assertNotIn('_scenario',snapshot);self.assertNotIn('scene_report',snapshot)

    def test_scenario_cycle_persists_and_does_not_repeat(self):
        first=[choose(self.e,[])['scenario_id'] for _ in range(80)]
        self.assertEqual(len(set(first)),80)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        next_ids=[choose(self.e,[])['scenario_id'] for _ in range(40)]
        self.assertFalse(set(first)&set(next_ids))
        snapshot=self.e.snapshot();self.assertNotIn('scenario_rotation',snapshot);self.assertNotIn('scenario_pool',snapshot)

    def test_address_cycle_covers_every_municipality_and_persists(self):
        first=choose_address(self.e)['city'];remaining=self.e.state['address_rotation'][:]
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertEqual(self.e.state['address_rotation'],remaining)
        seen=[first]+[choose_address(self.e)['city'] for _ in range(len(ADDRESS_CITIES)-1)]
        self.assertCountEqual(seen,ADDRESS_CITIES)
        self.assertNotEqual(choose_address(self.e)['city'],seen[-1])

    def test_bundled_address_coverage_and_real_osm_provenance(self):
        import json,sys
        from pathlib import Path
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from import_zone5_addresses import MUNICIPALITIES
        data=json.loads((Path(__file__).resolve().parents[1]/'app/data/addresses.json').read_text())
        expected={t for names in MUNICIPALITIES.values() for t in names.split('|')}
        self.assertEqual(set(ADDRESS_CITIES),expected)
        self.assertEqual(len(expected),84)
        from locations import ADDRESSES
        addresses=ADDRESSES;self.assertEqual(len(addresses),len({a['id'] for a in addresses}))
        self.assertGreaterEqual(len(addresses),2600)
        for a in addresses:
            self.assertTrue(a['street']);self.assertTrue(a['house_number'])
            self.assertIn(a['osm_type'],('node','way'))
            self.assertEqual(a['id'],f"osm-{a['osm_type']}-{a['osm_id']}")
            self.assertTrue(47.7<a['lat']<48.4 and 15.7<a['lon']<17.2)
        self.assertEqual(data['license'],'ODbL-1.0')
