import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from engine import Engine

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory(); self.path=str(Path(self.dir.name)/'test.db'); self.e=Engine(self.path)
    def tearDown(self):
        self.e.db.close(); self.dir.cleanup()
    def test_transport_does_not_ring_144(self):
        self.e.command('generate',{'kind':'transport'})
        j=self.e.state['jobs'][-1]
        self.assertTrue(j['accepted']); self.assertEqual(j['kind'],'transport')
        self.assertFalse(any(l['channel']=='Telefon' for l in self.e.state['logs']))
    def test_call_requires_acceptance_and_prevents_double_dispatch(self):
        self.e.command('generate',{'kind':'emergency'}); j=self.e.state['jobs'][-1]
        v=next(v for v in self.e.state['vehicles'] if v['type']=='RTW')
        payload={'job':j['id'],'vehicles':[v['id']]}
        with self.assertRaises(ValueError): self.e.command('dispatch',payload)
        self.e.command('accept',{'id':j['id']}); self.e.command('dispatch',payload)
        with self.assertRaises(ValueError): self.e.command('dispatch',payload)
        self.assertEqual(j['vehicles'],[v['id']])
    def test_dispatch_is_atomic(self):
        self.e.command('generate',{'kind':'transport'}); j=self.e.state['jobs'][-1]
        ktw=next(v for v in self.e.state['vehicles'] if v['type']=='KTW'); nef=next(v for v in self.e.state['vehicles'] if v['type']=='NEF')
        with self.assertRaises(ValueError): self.e.command('dispatch',{'job':j['id'],'vehicles':[ktw['id'],nef['id']]})
        self.assertIsNone(ktw['job']);self.assertEqual(j['vehicles'],[])
    def test_shift_overnight_and_unstaffed(self):
        v=copy.deepcopy(self.e.state['vehicles'][0]);v.update(start='20:00',end='06:00');self.e.state['clock']=23*3600
        self.assertTrue(self.e.in_shift(v));self.e.state['clock']=12*3600;self.assertFalse(self.e.in_shift(v))
        v.update(start='00:00',end='00:00',staffed=False);self.assertFalse(self.e.in_shift(v))
    def test_full_lifecycle(self):
        self.e.command('generate',{'kind':'transport'});j=self.e.state['jobs'][-1];v=next(v for v in self.e.state['vehicles'] if v['type']=='KTW')
        self.e.command('dispatch',{'job':j['id'],'vehicles':[v['id']]})
        self.e.command('control',{'paused':False})
        for expected in ['enroute','scene','transport','hospital','return','clean','ready']:
            duration=v['phase_due']-self.e.state['clock']+.1;self.e.tick(duration);self.assertEqual(v['status'],expected)
        self.assertEqual(j['status'],'done');self.assertIsNone(v['job'])
    def test_invalid_import_preserves_data(self):
        old=self.e.snapshot()
        with self.assertRaises(ValueError): self.e.command('import',{'config':{'stations':old['stations'],'vehicles':[{'callsign':'broken','station':'missing'}]}})
        self.assertEqual(self.e.snapshot(),old)
    def test_missing_station_import_rolls_back(self):
        old=self.e.snapshot(); bad=copy.deepcopy(old); bad['vehicles'][0]['station']='missing'
        with self.assertRaises(ValueError): self.e.command('import',{'config':bad})
        self.assertEqual(self.e.snapshot(),old)
    def test_duplicate_ids_rejected(self):
        old=self.e.snapshot(); bad=copy.deepcopy(old); bad['vehicles'][1]['id']=bad['vehicles'][0]['id']
        with self.assertRaises(ValueError): self.e.command('import',{'config':bad})
        self.assertEqual(self.e.snapshot(),old)
    def test_valid_import_round_trip(self):
        old=self.e.snapshot();self.e.command('import',{'config':{'stations':old['stations'],'vehicles':old['vehicles']}})
        self.assertEqual(len(self.e.state['vehicles']),14)
    def test_restart_persists_config_and_simulation(self):
        self.e.command('generate',{'kind':'transport'});self.e.command('control',{'speed':15});new=Engine(self.path)
        self.assertEqual(new.snapshot(),self.e.snapshot());new.db.close()
    def test_reset_keeps_user_fleet(self):
        v=copy.deepcopy(self.e.state['vehicles'][0]);v['callsign']='CUSTOM';self.e.command('vehicle',v)
        self.e.command('generate',{'kind':'transport'});self.e.command('reset',{})
        self.assertEqual(self.e.state['jobs'],[]);self.assertEqual(self.e.state['vehicles'][0]['callsign'],'CUSTOM')

if __name__=='__main__':unittest.main()
