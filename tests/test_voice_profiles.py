import unittest
import test_fleet
from voice_profiles import profile,caller_profile,resource_profile
from spoken_text import address_reply,speech_text,number

class VoiceProfileTests(unittest.TestCase):
    def test_leo_identity_does_not_depend_on_text(self):
        self.assertEqual(profile('LEO'),{'model':'leo','speaker_id':0,'identity':'LEO'})
    def test_call_keeps_one_identity_after_restore_and_context_changes(self):
        import json
        j={'id':'call-123','call':{}}
        expected=caller_profile(j)
        restored=json.loads(json.dumps(j));restored['title']='Neues Stichwort'
        self.assertEqual(caller_profile(restored),expected)
        self.assertNotEqual(expected,profile('caller:other-job'))
    def test_resource_voice_is_stable_across_status_and_callsign_changes(self):
        v={'id':'vehicle-1','callsign':'77/001','status':'ready'};expected=resource_profile(v)
        v.update(callsign='77/099',status='scene')
        self.assertEqual(resource_profile(v),expected)
        self.assertTrue(0<=expected['speaker_id']<236)
        self.assertNotEqual(expected,resource_profile({'id':'vehicle-2'}))
    def test_address_reply_uses_structured_facts_without_changing_postcode(self):
        job={'address':'Hauptplatz 6, 2563 Pottenstein','address_point':{'street':'Hauptplatz','house_number':'6','postcode':'2563','city':'Pottenstein'}}
        reply=address_reply(job)
        self.assertEqual(reply,'Ja, wir sind am Hauptplatz Nummer 6 in 2563 Pottenstein.')
        spoken=speech_text(reply)
        self.assertIn('Nummer sechs',spoken);self.assertIn('fünfundzwanzig dreiundsechzig Pottenstein',spoken)
        self.assertNotIn('2363',reply)
        job['address_point']=None;self.assertEqual(address_reply(job),reply)
    def test_house_suffix_street_grammar_and_radio_zeroes_are_preserved(self):
        self.assertEqual(address_reply({'address':'Hauptstraße 6a, 2320 Schwechat'}),'Ja, wir sind in der Hauptstraße Nummer 6a in 2320 Schwechat.')
        self.assertEqual(speech_text('LEO von 77/001, kommen.'),'LEO von siebenundsiebzig null null eins, kommen.')
        self.assertEqual(number(26),'sechsundzwanzig');self.assertEqual(number(21),'einundzwanzig')
