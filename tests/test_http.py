import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=Path(__file__).resolve().parents[1],env={**os.environ,'DATA_DIR':cls.temp.name},stdout=subprocess.DEVNULL)
        for _ in range(40):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);return
            except OSError:time.sleep(.05)
        cls.proc.terminate();raise RuntimeError('Server did not start')
    @classmethod
    def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=5);cls.temp.cleanup()
    def setUp(self):
        result=json.load(self.req('/api/session/create',{'name':'Julian'}));self.token=result['token']
    def req(self,path,data=None,token=None):
        headers={'Content-Type':'application/json'}
        if token is None:token=getattr(self,'token','')
        if token:headers['Authorization']='Bearer '+token
        return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8080'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers),timeout=3)
    def test_serves_ui_and_state(self):
        self.assertIn(b'app.js',self.req('/').read());self.assertTrue({'52/351','52/601','64/332','64/401'}<={v['callsign'] for v in json.load(self.req('/api/state'))['vehicles']});self.assertTrue({'c15','c16'}<={s['id']for s in json.load(self.req('/api/config'))['stations']})
    def test_generate_and_bad_request(self):
        state=json.load(self.req('/api/generate',{'kind':'transport'}));self.assertEqual(state['jobs'][-1]['kind'],'transport')
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/api/control',{'speed':999})
        self.assertEqual(err.exception.code,400)
    def test_speech_requires_auth_and_does_not_accept_arbitrary_text(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.req('/api/call_audio?job=x&line=0',token='')
        self.assertEqual(error.exception.code,401)
        with self.assertRaises(urllib.error.HTTPError) as error:self.req('/api/call_audio?job=x&line=0')
        self.assertEqual(error.exception.code,503)
    def test_unknown_route(self):
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/missing')
        self.assertEqual(err.exception.code,404)
    def test_unauthenticated_state_is_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/api/state',token='')
        self.assertEqual(err.exception.code,401)
    def test_guest_permission_and_session_join(self):
        code=json.load(self.req('/api/state'))['session']['code'];guest=json.load(self.req('/api/session/join',{'code':code,'name':'Gast'}))
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/api/reset',{},token=guest['token'])
        self.assertEqual(err.exception.code,403)
    def test_session_chat(self):
        state=json.load(self.req('/api/chat',{'text':'Hallo Team'}));self.assertEqual(state['chat'][-1]['text'],'Hallo Team')
    def test_authenticated_live_stream_pushes_changes(self):
        with self.req('/api/live') as response:
            self.assertIn('text/event-stream',response.headers['Content-Type'])
            def state_event():
                while True:
                    line=response.readline().decode()
                    if line.startswith('data: '):return json.loads(line[6:])
            first=state_event();self.assertEqual(first['session']['me'],json.load(self.req('/api/state'))['session']['me'])
            self.req('/api/chat',{'text':'Live ohne Polling'}).close()
            pushed=state_event();self.assertEqual(pushed['chat'][-1]['text'],'Live ohne Polling')
    def test_live_stream_requires_membership(self):
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/api/live',token='')
        self.assertEqual(err.exception.code,401)
if __name__=='__main__':unittest.main()
