import unittest
import test_fleet as helpers

class SupportTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle

    def job(self,kind='emergency'):
        j=self.e.new_job(kind,manual=True);j['accepted']=True
        self.e.command('edit_job',{'job':j['id'],'code':j['code']})
        return j

    def answer(self):
        self.e.command('control',{'paused':False});self.e.tick(45)

    def test_c15_requires_request_and_is_assigned_to_correct_incident(self):
        j=self.job();v=self.vehicle('C15')
        self.assertFalse(self.e.sendable(v,j))
        with self.assertRaises(ValueError):self.e.command('dispatch',{'job':j['id'],'vehicles':[v['id']]})
        self.e.command('support_request',{'job':j['id'],'vehicle':v['id'],'reason':'Lokale Notarztmittel gebunden'})
        self.assertIsNone(v['job']);self.e.tick(60);self.assertEqual(j['support_requests'][0]['state'],'pending')
        self.answer();self.assertEqual(j['support_requests'][0]['state'],'accepted')
        self.assertEqual(v['job'],j['id']);self.assertEqual(j['vehicles'],[v['id']])
        self.assertEqual({m['channel']for m in self.e.state['messages']if m['vehicle']==v['id']},{'SDS','ESApp'})
        self.e.acknowledge(v,direct=True);self.assertEqual(v['status'],'enroute');self.assertEqual(v['route_state'],'flight')
        self.assertEqual(v['leg']['target_lat'],j['lat'])

    def test_second_job_cannot_take_same_helicopter(self):
        j=self.job();other=self.job();v=self.vehicle('C15')
        self.e.command('support_request',{'job':j['id'],'vehicle':v['id']})
        with self.assertRaises(ValueError):self.e.command('support_request',{'job':j['id'],'vehicle':v['id']})
        self.e.command('support_request',{'job':other['id'],'vehicle':v['id']});self.answer()
        self.assertEqual(v['job'],j['id']);self.assertEqual(other['support_requests'][0]['state'],'declined')
        self.assertEqual(other['vehicles'],[])

    def test_retract_then_another_job_can_request(self):
        j=self.job();v=self.vehicle('C15')
        self.e.command('support_request',{'job':j['id'],'vehicle':v['id']})
        r=j['support_requests'][0]
        self.e.command('support_cancel',{'job':j['id'],'request':r['id']})
        self.assertFalse(v.get('support_request'));self.assertEqual(r['state'],'cancelled')
        other=self.job();self.e.command('support_request',{'job':other['id'],'vehicle':v['id']});self.answer()
        self.assertEqual(v['job'],other['id'])

    def test_out_of_service_and_finished_job_receive_no_resource(self):
        j=self.job();v=self.vehicle('C15');self.e.command('vehicle_status',{'vehicle':v['id'],'status':'0'})
        self.e.command('support_request',{'job':j['id'],'vehicle':v['id']});self.answer()
        self.assertEqual(j['support_requests'][0]['state'],'declined');self.assertIsNone(v['job'])
        v=self.vehicle('C16');self.e.command('support_request',{'job':j['id'],'vehicle':v['id']});j['status']='done';self.answer()
        self.assertEqual(j['support_requests'][-1]['state'],'cancelled');self.assertFalse(v.get('support_request'))

    def test_other_federal_state_and_ground_types(self):
        self.e.command('station',{'id':'test-bg','name':'Übungsstützpunkt Burgenland','zone':'Burgenland','dispo':'BG','region':'Burgenland','lat':47.9,'lon':16.5})
        for typ in ('KTW','RTW','NEF'):
            self.e.command('vehicle',{'id':'test-'+typ,'callsign':'TEST-'+typ,'type':typ,'station':'test-bg','start':'00:00','end':'00:00','staffed':True})
            j=self.job('transport' if typ=='KTW' else 'emergency');v=self.vehicle('TEST-'+typ)
            self.assertFalse(self.e.sendable(v,j))
            self.e.command('support_request',{'job':j['id'],'vehicle':v['id']});self.answer()
            self.assertEqual(v['job'],j['id'])
        self.assertTrue(any(x['region']=='Burgenland'for x in self.e.snapshot()['support_catalog']))

    def test_ownership_and_return_home(self):
        j=self.job();j['owner']='a';v=self.vehicle('C15')
        with self.assertRaises(ValueError):self.e.command('support_request',{'job':j['id'],'vehicle':v['id'],'_actor':{'id':'b'}})
        self.e.command('support_request',{'job':j['id'],'vehicle':v['id'],'_actor':{'id':'a'}});self.answer()
        self.e.command('resource_call',{'job':j['id'],'vehicle':v['id']})
        c=self.e.state['radio_calls'][-1]
        self.e.command('cancel_radio',{'job':j['id'],'call':c['id'],'step':'answer'})
        self.e.command('cancel_radio',{'job':j['id'],'call':c['id'],'step':'cancel'})
        self.e.update_support(self.e.state['clock'])
        self.assertFalse(v.get('support_job'));self.assertFalse(self.e.sendable(v,self.job()))

    def test_reset_clears_pending_loans_and_no_leadership_seed(self):
        self.assertFalse(any(v['type']=='BEL'for v in self.e.state['vehicles']))
        j=self.job();v=self.vehicle('C15');self.e.command('support_request',{'job':j['id'],'vehicle':v['id']})
        self.e.command('reset',{})
        self.assertFalse(self.vehicle('C15').get('support_request'));self.assertEqual(self.e.state['jobs'],[])

if __name__=='__main__':unittest.main()
