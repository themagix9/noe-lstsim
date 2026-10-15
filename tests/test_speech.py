import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import test_fleet
from speech import Speech

class SpeechTests(unittest.TestCase):
    def test_cached_audio_never_waits_on_a_future_utterance(self):
        s=Speech();s.cache[('Hallo','LEO')]=b'RIFFcached'
        with patch.object(s,'available',return_value=True):
            s.lock.acquire()
            try:self.assertEqual(s.synthesize('Hallo','LEO'),b'RIFFcached')
            finally:s.lock.release()
    def test_prepare_is_bounded_and_synthesizes_future_lines_in_order(self):
        s=Speech();done=threading.Event();rows=[]
        def synth(text,speaker):
            rows.append((text,speaker))
            if text=='zweite':done.set()
            return b'RIFF'
        with patch.object(s,'available',return_value=True),patch.object(s,'synthesize',side_effect=synth):
            s.prepare([{'text':'erste','speaker':'LEO'},{'text':'zweite','speaker':'Anrufer'}])
            self.assertTrue(done.wait(2));self.assertEqual(rows,[('erste','LEO'),('zweite','Anrufer')])
    def test_missing_model_does_not_start_preparation_or_block_text_calls(self):
        s=Speech()
        with patch.object(s,'available',return_value=False):
            s.prepare([{'text':'Hallo','speaker':'LEO'}]);self.assertIsNone(s.worker)
            with self.assertRaises(ValueError):s.synthesize('Hallo','LEO')
