from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from aao import CODES,SOURCE,code_rule
from engine import Engine

class AAOTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.e=Engine(str(Path(self.temp.name)/'db'));self.j=self.e.new_job('emergency');self.j['accepted']=True
        for v in self.e.state['vehicles']:v.update(status='out',manual_out=True)
    def tearDown(self):self.e.db.close();self.temp.cleanup()
    def choose(self,typ,delta=0,nfs=False):
        v=next(v for v in self.e.state['vehicles'] if v['type']==typ and v['status']=='out');v.update(status='ready',manual_out=False,lat=self.j['lat']+delta,lon=self.j['lon'],nfs=nfs,turnout=0);return v
    def code(self,code):self.e.edit_job({'job':self.j['id'],'code':code})
    def suggestion(self):return self.e.recommendation(self.j)
    def test_source_count_date_and_category(self):
        self.assertEqual(len(CODES),2650);self.assertEqual(SOURCE['date'],'2025-02-21');self.assertEqual(CODES['RD-1A1']['category'],'BLS gelb');self.assertIn('ALP-45A1',CODES)
        self.assertEqual(CODES['RD-22D2M']['category'],'ALS orange');self.assertIn('RD-32B2 ASB-RUFHILFE',CODES)
    def test_bls_red_90_seconds_preference(self):
        self.code('RD-17B1');ktw=self.choose('KTW');rtw=self.choose('RTW',.006)
        self.assertEqual(self.suggestion()['vehicles'],[rtw['id']]);rtw['lat']=self.j['lat']+.03;self.assertEqual(self.suggestion()['vehicles'],[ktw['id']])
    def test_ktwb_not_suggested_for_rd(self):
        self.code('RD-1A1');v=self.choose('KTW');v['type']='KTW-B';self.assertFalse(self.suggestion()['vehicles']);self.assertFalse(self.e.eligible(v,self.j))
    def test_als_green_needs_confirmed_nfs(self):
        self.code('RD-6C1');v=self.choose('RTW');self.assertIn('RTW/RTW-C mit bestätigtem NFS',self.suggestion()['missing']);v['nfs']=True;self.assertEqual(self.suggestion()['vehicles'],[v['id']])
    def test_als_yellow_fallback_adds_nef(self):
        self.code('RD-6D2');v=self.choose('RTW');nef=self.choose('NEF');self.assertEqual(self.suggestion()['vehicles'],[v['id'],nef['id']]);v['nfs']=True;self.assertEqual(self.suggestion()['vehicles'],[v['id']])
    def test_secondary_has_no_vehicle_until_fallback(self):
        self.code('RD-1A2');v=self.choose('KTW');self.assertEqual(self.suggestion()['vehicles'],[])
        self.e.edit_job({'job':self.j['id'],'code':'RD-1A2','secondary_unavailable':True});self.assertEqual(self.suggestion()['vehicles'],[v['id']])
    def test_als_orange_nef_and_missing_special_rules(self):
        self.code('RD-31D3');v=self.choose('RTW');nef=self.choose('NEF');r=self.suggestion();self.assertEqual(r['vehicles'],[v['id'],nef['id']]);self.assertTrue(any('NAH' in w for w in r['warnings']))
    def test_custom_aao_no_duplicate_resource(self):
        self.e.edit_rules({'rules':[{'code':'SIM-DOUBLE','title':'Doppeltest','kind':'emergency','priority':'mittel','needs':['RTW','RTW'],'signal':False}]});self.code('SIM-DOUBLE');a=self.choose('RTW');b=self.choose('RTW');r=self.suggestion();self.assertEqual(set(r['vehicles']),{a['id'],b['id']})
    def test_manual_creation_does_not_ring144(self):
        count=sum(l['channel']=='Telefon' for l in self.e.state['logs']);j=self.e.create_job({'code':'RD-1A1','address':'Testadresse','lat':48.1,'lon':16.4});self.assertTrue(j['accepted']);self.assertEqual(j['category'],'BLS gelb');self.assertEqual(sum(l['channel']=='Telefon' for l in self.e.state['logs']),count)
    def test_invalid_manual_creation_and_rule_update_are_atomic(self):
        before=self.e.snapshot()
        with self.assertRaises(ValueError):self.e.command('create_job',{'code':'RD-1A1','address':'Test','lat':999,'lon':16})
        self.assertEqual(self.e.snapshot(),before)
        with self.assertRaises(ValueError):self.e.command('rules',{'rules':[{'code':'bad'}]})
        self.assertEqual(self.e.snapshot(),before)
