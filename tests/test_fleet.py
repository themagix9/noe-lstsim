import copy
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from engine import Engine
from daylight import window

class FleetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=str(Path(self.tmp.name)/'db.sqlite');self.e=Engine(self.path)
    def tearDown(self):self.e.db.close();self.tmp.cleanup()
    def vehicle(self,call):return next(v for v in self.e.state['vehicles'] if v['callsign']==call)
    def job(self,kind='emergency'):
        j=self.e.new_job(kind);j['accepted']=True;return j
    def test_confirmed_station_bindings(self):
        expected={'77/006':'goetzendorf','77/030':'goetzendorf','77/060':'leopoldsdorf','77/050':'himberg'}
        for call,station in expected.items():self.assertEqual(self.vehicle(call)['station'],station)
        self.assertEqual(self.vehicle('77/015')['type'],'RTW');self.assertEqual(self.vehicle('77/020')['type'],'BKTW')
        self.assertEqual(len([v for v in self.e.state['vehicles'] if v['station']=='schwechat' and v['type'] in ('RTW','RTW-C','KTW','BKTW')]),15)
    def test_capable_fleet_and_one_active_per_station(self):
        capable=[v['callsign'] for v in self.e.state['vehicles'] if v['callsign'].startswith('77/') and v.get('rtwc_capable')]
        self.assertCountEqual(capable,['77/001','77/002','77/004','77/030'])
        for station in self.e.state['stations']:
            active=[v for v in self.e.state['vehicles'] if v['station']==station['id'] and v['type']=='RTW-C']
            self.assertLessEqual(len(active),1);self.assertTrue(all(v['nfs'] for v in active))
    def test_switch_downgrades_previous_and_confirms_nfs(self):
        self.e.command('rtwc',{'vehicle':self.vehicle('77/004')['id']})
        self.assertEqual(self.vehicle('77/001')['type'],'RTW');self.assertEqual(self.vehicle('77/004')['type'],'RTW-C');self.assertTrue(self.vehicle('77/004')['nfs'])
    def test_switch_rejects_busy_and_incapable(self):
        j=self.job();self.e.dispatch({'job':j['id'],'vehicles':[self.vehicle('77/001')['id']]})
        with self.assertRaises(ValueError):self.e.command('rtwc',{'vehicle':self.vehicle('77/004')['id']})
        with self.assertRaises(ValueError):self.e.command('rtwc',{'vehicle':self.vehicle('77/011')['id']})
    def test_vehicle_editor_cannot_add_second_c_or_remove_fixed(self):
        data=copy.deepcopy(self.vehicle('77/002'));data.update(type='RTW-C',nfs=True)
        with self.assertRaises(ValueError):self.e.edit_vehicle(data)
        data=copy.deepcopy(self.vehicle('77/030'));data['type']='RTW'
        with self.assertRaises(ValueError):self.e.edit_vehicle(data)
    def test_ktw_and_rtw_can_do_both_job_kinds(self):
        for kind in ('transport','emergency'):
            for call in ('77/003','77/011'):
                self.assertTrue(self.e.eligible(self.vehicle(call),self.job(kind)))
        self.assertFalse(self.e.eligible(self.vehicle('77/020'),self.job()))
    def test_fr_responds_but_never_transports_or_fulfils_aao(self):
        fr=self.vehicle('FR-SCH-01');j=self.job();j.update(category='ALS rot',priority='hoch')
        self.assertFalse(self.e.eligible(fr,self.job('transport')))
        self.e.dispatch({'job':j['id'],'vehicles':[fr['id']]});self.e.depart(fr);self.e.advance(fr);self.e.advance(fr)
        self.assertIsNone(fr['job']);self.assertNotEqual(fr['status'],'transport')
        self.assertEqual(j['bed_state'],'none');self.assertNotEqual(j['status'],'done')
    def test_fr_count_and_fischamend_unknown_pool(self):
        self.assertEqual(len([v for v in self.e.state['vehicles'] if v['type']=='FR' and v['station']=='schwechat']),10)
        self.assertEqual(self.vehicle('FR-FISCHAMEND-POOL')['organization'],'FR Fischamend');self.assertFalse(self.vehicle('FR-FISCHAMEND-POOL')['staffed'])
    def test_c3_c9_daylight_and_night_unavailable(self):
        self.e.state['start_date']='2026-12-21'
        for call in ('C3','C9'):
            v=self.vehicle(call);self.e.state['clock']=12*3600;self.assertTrue(self.e.in_shift(v))
            self.e.state['clock']=3*3600;self.assertFalse(self.e.in_shift(v));self.assertFalse(self.e.sendable(v,self.job()))
        start,end=window('2026-06-21',48.18,16.41);self.assertEqual(start,360);self.assertGreater(end,20*60)
        start,end=window('2026-12-21',48.18,16.41);self.assertGreater(start,7*60);self.assertLess(end,17*60)
    def test_als_orange_prefers_nef_under_15_min_red_fastest(self):
        self.e.state['clock']=12*3600;j=self.job();j.update(lat=48.1844,lon=16.4136,category='ALS orange',priority='hoch')
        ids=self.e.recommendation(j)['vehicles'];types=[self.e.get('vehicles',id)['type'] for id in ids];self.assertIn('NEF',types)
        j['category']='ALS rot';ids=self.e.recommendation(j)['vehicles'];self.assertIn('NAH',[self.e.get('vehicles',id)['type'] for id in ids])
    def test_migration_and_switch_persist_without_duplicates(self):
        self.e.command('rtwc',{'vehicle':self.vehicle('77/002')['id']});count=len(self.e.state['vehicles']);self.e.db.close();self.e=Engine(self.path)
        self.assertEqual(len(self.e.state['vehicles']),count);self.assertEqual(self.vehicle('77/002')['type'],'RTW-C')
    def test_config_roundtrip_preserves_fixed_and_daylight(self):
        snapshot=self.e.snapshot();self.e.command('import',{'config':{'stations':snapshot['stations'],'vehicles':snapshot['vehicles']}})
        self.assertTrue(self.vehicle('77/030')['rtwc_fixed']);self.assertTrue(self.vehicle('C3')['daylight'])

if __name__=='__main__':unittest.main()
