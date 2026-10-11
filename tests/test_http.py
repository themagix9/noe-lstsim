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
        cls.temp=tempfile.TemporaryDirectory()
        cls.proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=Path(__file__).resolve().parents[1],env={**os.environ,'DATA_DIR':cls.temp.name},stdout=subprocess.DEVNULL)
        for _ in range(40):
            try: urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);return
            except OSError: time.sleep(.05)
        cls.proc.terminate(); raise RuntimeError('Server did not start')
    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait(timeout=5);cls.temp.cleanup()
    def req(self,path,data=None):
        return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8080'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'}),timeout=3)
    def test_serves_ui_and_state(self):
        self.assertIn(b'app.js',self.req('/').read())
        self.assertEqual(len(json.load(self.req('/api/state'))['vehicles']),14)
        self.assertEqual(len(json.load(self.req('/api/config'))['stations']),3)
    def test_generate_and_bad_request(self):
        state=json.load(self.req('/api/generate',{'kind':'transport'}));self.assertEqual(state['jobs'][-1]['kind'],'transport')
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/api/control',{'speed':999})
        self.assertEqual(err.exception.code,400)
    def test_unknown_route(self):
        with self.assertRaises(urllib.error.HTTPError) as err:self.req('/missing')
        self.assertEqual(err.exception.code,404)
if __name__=='__main__':unittest.main()
