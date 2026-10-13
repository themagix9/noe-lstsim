import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from engine import Engine
from fleet_zone5 import inventory, upgrade

class Zone5FleetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=str(Path(self.tmp.name)/'db.sqlite');self.e=Engine(self.path)
    def tearDown(self):self.e.db.close();self.tmp.cleanup()
    def vehicle(self,call):return next(v for v in self.e.state['vehicles'] if v['callsign']==call)
    def test_operator_and_district_inventory(self):
        for call,typ,home,source,verification in inventory():
            v=self.vehicle(call);self.assertEqual((v['type'],v['station']),(typ,home));self.assertEqual(v['inventory_source'],source);self.assertTrue(v['verification']);self.assertEqual(self.e.station(home)['dispo'],'05')
        for call in ('52/357','52/358','52/005','52/009','52/604','52/842','53/409','77/022'):
            self.assertNotIn(call,{v['callsign'] for v in self.e.state['vehicles']})
        self.assertEqual({self.e.station(v['station'])['zone'] for v in self.e.state['vehicles'] if v.get('inventory_source')},{'Baden','Mödling','Bruck/Leitha'})
    def test_upgrade_saved_room_is_additive_and_keeps_manual_override(self):
        target=self.vehicle('52/351');target.update(type='KTW',source='Manuell korrigiert')
        self.e.state['vehicles']=[v for v in self.e.state['vehicles'] if v.get('inventory_source') is None or v['callsign']=='52/351']
        self.e.state['zone5_fleet_version']=0;upgrade(self.e)
        self.assertEqual(target['type'],'KTW');self.assertEqual(target['source'],'Manuell korrigiert')
        calls=[v['callsign'] for v in self.e.state['vehicles']];self.assertEqual(len(calls),len(set(calls)))
        self.assertEqual(self.vehicle('77/030')['type'],'RTW-C');self.assertEqual(self.vehicle('77/006')['station'],'goetzendorf')
        self.e.save();self.e.db.close();self.e=Engine(self.path);self.assertEqual(self.vehicle('52/351')['type'],'KTW')
    def test_deleted_candidate_is_not_resurrected_after_reset_or_restart(self):
        self.e.state['vehicles']=[v for v in self.e.state['vehicles'] if v['callsign']!='52/844'];self.e.command('reset',{})
        self.e.db.close();self.e=Engine(self.path);self.assertNotIn('52/844',{v['callsign'] for v in self.e.state['vehicles']})
    def test_rosters_include_new_units_without_fake_c_qualification(self):
        self.e.state['clock']=8*3600
        self.assertTrue(all(self.e.in_shift(self.vehicle(call)) for call,*_ in inventory()))
        self.e.state['clock']=22*3600;plan=set(self.e.staff_plan())
        for station in ('kottingbrunn','asb-traiskirchen','moedling','brunn'):
            self.assertGreaterEqual(sum(v['id'] in plan for v in self.e.state['vehicles'] if v['station']==station),3)
        self.assertFalse(self.vehicle('64/009')['nfs']);self.assertEqual(self.vehicle('64/009')['type'],'RTW')

if __name__=='__main__':unittest.main()
