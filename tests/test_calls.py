import unittest
import test_fleet as helpers

class CallTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    def call(self):
        j=self.e.new_job('emergency');self.e.command('accept',{'id':j['id']});return j
    def test_greeting_and_stepwise_answers(self):
        j=self.call();self.assertEqual(j['call']['state'],'connected');self.assertEqual(j['call']['transcript'][0]['speaker'],'LEO')
        self.assertIn('wo genau ist der Notfallort',j['call']['transcript'][0]['text']);self.assertIn(j['address'],j['call']['transcript'][1]['text'])
        with self.assertRaises(ValueError):self.e.command('call_question',{'job':j['id'],'question':'breathing'})
        for q in j['call']['questions']:self.e.command('call_question',{'job':j['id'],'question':q['key']})
        self.assertEqual(j['call']['state'],'ready');self.assertTrue(j['asked']);self.assertEqual(len(j['call']['transcript']),14)
    def test_finish_requires_complete_abfrage_and_persists(self):
        j=self.call()
        with self.assertRaises(ValueError):self.e.command('call_finish',{'job':j['id']})
        for q in j['call']['questions']:self.e.command('call_question',{'job':j['id'],'question':q['key']})
        self.e.command('call_finish',{'job':j['id']});self.assertEqual(j['call']['state'],'ended')
        self.assertIn('Wir schicken jemanden',j['call']['transcript'][-2]['text'])
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertEqual(self.e.get('jobs',j['id'])['call']['state'],'ended')
    def test_dispatch_finishes_ready_call_without_duplicate_goodbye(self):
        j=self.call();v=self.vehicle('77/002')
        with self.assertRaises(ValueError):self.e.command('dispatch',{'job':j['id'],'vehicles':[v['id']]})
        for q in j['call']['questions']:self.e.command('call_question',{'job':j['id'],'question':q['key']})
        self.e.command('dispatch',{'job':j['id'],'vehicles':[v['id']]});self.assertEqual(j['call']['state'],'ended')
        self.assertEqual(sum('Wir schicken jemanden' in line['text'] for line in j['call']['transcript']),1)
    def test_other_dispatcher_cannot_answer(self):
        j=self.call();j['owner']='a'
        with self.assertRaises(ValueError):self.e.command('call_question',{'job':j['id'],'question':'location','_actor':{'id':'b'}})

    def test_combined_buttons_complete_six_topics_in_three_steps(self):
        j=self.call()
        for key,answered in [('location',2),('patient',5),('access',6)]:
            self.e.command('call_question',{'job':j['id'],'question':key,'combined':True})
            self.assertEqual(len(j['call']['answered']),answered)
        self.assertEqual(j['call']['state'],'ready');self.assertEqual(len(j['call']['transcript']),8)
        text=' '.join(line['text'] for line in j['call']['transcript'])
        for q in j['call']['questions']:self.assertIn(q['answer'],text)
        self.e.command('call_finish',{'job':j['id']});self.assertEqual(len(j['call']['transcript']),10)

    def test_combined_mode_resumes_partly_queried_existing_call(self):
        j=self.call();self.e.command('call_question',{'job':j['id'],'question':'location'})
        self.e.command('call_question',{'job':j['id'],'question':'event','combined':True})
        self.assertEqual(j['call']['answered'],['location','event'])
        self.e.command('call_question',{'job':j['id'],'question':'patient','combined':True})
        with self.assertRaises(ValueError):self.e.command('call_finish',{'job':j['id']})
        self.e.command('call_question',{'job':j['id'],'question':'access','combined':True})
        self.assertEqual(j['call']['state'],'ready')
