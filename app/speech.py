"""Local neural TTS. One CPU model, bounded cache and ahead-of-playback preparation."""
from collections import OrderedDict
import io
import json
import os
from pathlib import Path
import queue
import threading
import wave

class Speech:
    def __init__(self):
        self.lock=threading.Lock();self.cache_lock=threading.RLock();self.voice=None;self.cache=OrderedDict();self.size=0
        self.model=Path(os.environ.get('TTS_MODEL','/opt/voices/de_DE-thorsten-high.onnx'))
        self.preparation=queue.Queue(maxsize=256);self.worker=None
    def available(self):return os.environ.get('TTS_ENABLED','1')!='0' and self.model.is_file()
    def cached(self,key):
        with self.cache_lock:
            raw=self.cache.get(key)
            if raw is not None:self.cache.move_to_end(key)
            return raw
    def prepare(self,rows):
        if not self.available():return
        with self.cache_lock:
            if self.worker is None:
                self.worker=threading.Thread(target=self._prepare,daemon=True,name='caller-speech');self.worker.start()
        for row in rows:
            key=(row['text'],row['speaker'])
            if self.cached(key) is not None:continue
            try:self.preparation.put_nowait(key)
            except queue.Full:break
    def _prepare(self):
        import time
        while True:
            text,speaker=self.preparation.get()
            try:self.synthesize(text,speaker)
            except Exception:pass # Foreground request reports an unavailable model.
            finally:self.preparation.task_done()
            # Give an uncached foreground utterance priority over another future line.
            time.sleep(.02)
    def synthesize(self,text,speaker):
        if not self.available():raise ValueError('Sprachmodell nicht verfügbar; Gespräch läuft als Text weiter.')
        key=(text,speaker);raw=self.cached(key)
        if raw is not None:return raw
        # Cached playback does not wait on synthesis of a different future line.
        if not self.lock.acquire(timeout=15):raise ValueError('Sprachausgabe ausgelastet; Gespräch läuft als Text weiter.')
        try:
            raw=self.cached(key)
            if raw is not None:return raw
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
            with self.cache_lock:
                while self.cache and (len(self.cache)>=128 or self.size+len(raw)>32_000_000):
                    _,old=self.cache.popitem(last=False);self.size-=len(old)
                if len(raw)<=4_000_000:self.cache[key]=raw;self.size+=len(raw)
            return raw
        finally:self.lock.release()

speech=Speech()
