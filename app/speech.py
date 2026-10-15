"""Local neural TTS. One loaded CPU model, bounded shared PCM cache, no cloud API."""
from collections import OrderedDict
import io
import json
import os
from pathlib import Path
import threading
import wave

class Speech:
    def __init__(self):
        self.lock=threading.Lock();self.voice=None;self.cache=OrderedDict();self.size=0
        self.model=Path(os.environ.get('TTS_MODEL','/opt/voices/de_DE-thorsten-high.onnx'))
    def synthesize(self,text,speaker):
        if os.environ.get('TTS_ENABLED','1')=='0' or not self.model.is_file():raise ValueError('Sprachmodell nicht verfügbar; Gespräch läuft als Text weiter.')
        key=(text,speaker)
        # Serialize model access, not engine/session locks. Parallel HTTP requests
        # share model/cache instead of each allocating another ONNX runtime.
        if not self.lock.acquire(timeout=15):raise ValueError('Sprachausgabe ausgelastet; Gespräch läuft als Text weiter.')
        try:
            if key in self.cache:
                self.cache.move_to_end(key);return self.cache[key]
            from piper import PiperVoice,SynthesisConfig
            from piper.config import PiperConfig
            if self.voice is None:
                import onnxruntime as ort
                session=ort.SessionOptions();session.intra_op_num_threads=2;session.inter_op_num_threads=1
                config=PiperConfig.from_dict(json.loads(Path(str(self.model)+'.json').read_text()))
                self.voice=PiperVoice(config=config,session=ort.InferenceSession(str(self.model),sess_options=session,providers=['CPUExecutionProvider']))
            out=io.BytesIO()
            with wave.open(out,'wb') as wav:
                self.voice.synthesize_wav(text,wav,syn_config=SynthesisConfig(length_scale=.85 if speaker=='Anrufer' else .9,noise_scale=.6,noise_w_scale=.7))
            raw=out.getvalue()
            while self.cache and (len(self.cache)>=128 or self.size+len(raw)>32_000_000):
                _,old=self.cache.popitem(last=False);self.size-=len(old)
            if len(raw)<=4_000_000:self.cache[key]=raw;self.size+=len(raw)
            return raw
        finally:self.lock.release()

speech=Speech()
