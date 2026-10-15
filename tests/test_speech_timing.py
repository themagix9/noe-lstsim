import io
import wave
from array import array
import unittest
import test_fleet
from speech_timing import natural_pauses

def wav(samples):
    out=io.BytesIO()
    with wave.open(out,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(array('h',samples).tobytes())
    return out.getvalue()
def samples(raw):
    with wave.open(io.BytesIO(raw),'rb') as f:return array('h',f.readframes(f.getnframes()))
class SpeechTimingTests(unittest.TestCase):
    def test_shorten_long_silence_without_touching_voiced_samples(self):
        voiced=[1000,-1000]*800
        before=wav([0]*8000+voiced+[0]*16000+voiced+[0]*8000);after=samples(natural_pauses(before))
        self.assertEqual([v for v in after if v],[*voiced,*voiced]);self.assertLess(len(after),12000)
    def test_quiet_consonants_and_short_natural_pauses_are_unchanged(self):
        raw=wav([150,-150]*16000+[0]*1600+[800,-800]*1600)
        self.assertEqual(natural_pauses(raw),raw)
