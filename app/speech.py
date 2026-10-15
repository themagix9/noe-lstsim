"""Local neural TTS. One clear CPU model, bounded cache and ahead-of-playback preparation."""
from collections import OrderedDict
import io
import json
import os
from pathlib import Path
import queue
import threading
import wave
from voice_profiles import profile as make_profile
from spoken_text import speech_text
from speech_timing import natural_pauses

class Speech:
    def __init__(self):
        self.lock=threading.Lock();self.cache_lock=threading.RLock();self.voice=None;self.voices={};self.cache=OrderedDict();self.size=0
        self.model=Path(os.environ.get('TTS_MODEL','/opt/voices/de_DE-thorsten-high.onnx'))
        self.female_model=Path(os.environ.get('TTS_FEMALE_MODEL','/opt/voices/de_DE-kerstin-low.onnx'))
        self.preparation=queue.Queue(maxsize=256);self.worker=None
    def available(self):return os.environ.get('TTS_ENABLED','1')!='0' and self.model.is_file()
    def cached(self,key):
        with self.cache_lock:
            raw=self.cache.get(key)
            if raw is not None:self.cache.move_to_end(key)
            return raw
    def audio_key(self,text,speaker,profile=None):
        return (text,speaker) if profile is None else (text,profile['model'],profile['speaker_id'],profile.get('identity'))
    def prepare(self,rows):
        if not self.available():return
        with self.cache_lock:
            if self.worker is None:
                self.worker=threading.Thread(target=self._prepare,daemon=True,name='caller-speech');self.worker.start()
        for row in rows:
            identity=row.get('voice_profile');key=self.audio_key(row['text'],row['speaker'],identity)
            if self.cached(key) is not None:continue
            try:self.preparation.put_nowait((row['text'],row['speaker'],identity))
            except queue.Full:break
    def _prepare(self):
        import time
        while True:
            text,speaker,identity=self.preparation.get()
            try:self.synthesize(text,speaker,identity) if identity is not None else self.synthesize(text,speaker)
            except Exception:pass # Foreground request reports an unavailable model.
            finally:self.preparation.task_done()
            # Give an uncached foreground utterance priority over another future line.
            time.sleep(.02)
    def synthesize(self,text,speaker,profile=None):
        if not self.available():raise ValueError('Sprachmodell nicht verfügbar; Gespräch läuft als Text weiter.')
        key=self.audio_key(text,speaker,profile);raw=self.cached(key)
        if raw is not None:return raw
        # Cached playback does not wait on synthesis of a different future line.
        if not self.lock.acquire(timeout=15):raise ValueError('Sprachausgabe ausgelastet; Gespräch läuft als Text weiter.')
        try:
            raw=self.cached(key)
            if raw is not None:return raw
            from piper import PiperVoice,SynthesisConfig
            from piper.config import PiperConfig
            identity=profile or make_profile('LEO' if speaker=='LEO' else 'caller:default')
            model=self.female_model if identity.get('model')=='female' else self.model
            voice_key='female-model' if identity.get('model')=='female' else 'clear-model'
            if identity.get('model')=='mls':identity=make_profile(identity.get('identity','caller:legacy'))
            if not model.is_file():raise ValueError('Zugeordnetes Sprachmodell fehlt.')
            if voice_key not in self.voices:
                import onnxruntime as ort
                session=ort.SessionOptions();session.intra_op_num_threads=2;session.inter_op_num_threads=1
                config=PiperConfig.from_dict(json.loads(Path(str(model)+'.json').read_text()))
                self.voices[voice_key]=PiperVoice(config=config,session=ort.InferenceSession(str(model),sess_options=session,providers=['CPUExecutionProvider']))
            voice=self.voices[voice_key]
            speaker_id=identity['speaker_id']
            if not 0<=speaker_id<voice.config.num_speakers:raise ValueError('Unbekannte Sprecherstimme.')
            out=io.BytesIO()
            with wave.open(out,'wb') as wav:
                voice.synthesize_wav(speech_text(text),wav,syn_config=SynthesisConfig(speaker_id=speaker_id,length_scale=1.0,noise_scale=.333,noise_w_scale=.333))
            raw=natural_pauses(out.getvalue())
            with self.cache_lock:
                while self.cache and (len(self.cache)>=128 or self.size+len(raw)>32_000_000):
                    _,old=self.cache.popitem(last=False);self.size-=len(old)
                if len(raw)<=4_000_000:self.cache[key]=raw;self.size+=len(raw)
            return raw
        finally:self.lock.release()

speech=Speech()
