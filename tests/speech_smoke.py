"""Run inside the built image: real German ONNX model, audio cache and call budget."""
import io
import json
import tempfile
import time
import wave
from pathlib import Path
from unittest.mock import patch
from engine import Engine,SCENARIOS
from speech import speech

with tempfile.TemporaryDirectory() as directory,patch.dict('os.environ',{'ROUTING_ENABLED':'0','CALL_AUTO':'1'}):
    engine=Engine(str(Path(directory)/'db'))
    started=time.monotonic()
    j=engine.new_job('emergency',scenario=SCENARIOS[1]);engine.accept_call(j)
    engine.call_playback({'job':j['id'],'mode':'speech'})
    rows=j['call']['transcript']+j['call']['pending'];duration=0;generated=0
    for row in rows:
        identity=j['call']['voice_profile'] if row['speaker']=='Anrufer' else None
        start=time.monotonic();raw=speech.synthesize(row['text'],row['speaker'],identity);generated+=time.monotonic()-start
        assert raw.startswith(b'RIFF') and len(raw)>1000
        with wave.open(io.BytesIO(raw),'rb') as wav:
            assert wav.getnchannels()==1 and wav.getsampwidth()==2
            seconds=wav.getnframes()/wav.getframerate()
        played=seconds+.12;duration+=played
        # Simulate the browser playing while later lines are prepared. This
        # measures end-to-end pacing, not only the sum of WAV durations.
        time.sleep(played)
        assert speech.synthesize(row['text'],row['speaker'],identity)==raw
    elapsed=time.monotonic()-started
    assert 20<=duration<=90,(duration,generated)
    assert 20<=elapsed<=100,(elapsed,generated)
    print(json.dumps({'model':'de_DE-thorsten-high','lines':len(rows),'spoken_seconds':round(duration,2),'foreground_wait_seconds':round(generated,2),'conversation_elapsed_seconds':round(elapsed,2),'cache_entries':len(speech.cache),'caller_voice':j['call']['voice_profile'],'native_playback':True}))
    from voice_profiles import resource_profile
    v=next(v for v in engine.state['vehicles'] if v['callsign']=='77/002')
    identity=resource_profile(v)
    sample=speech.synthesize('LEO von siebenundsiebzig null null zwei, kommen.',v['callsign'],identity)
    assert sample.startswith(b'RIFF') and len(sample)>1000
    assert speech.synthesize('LEO von siebenundsiebzig null null zwei, kommen.',v['callsign'],identity)==sample
    from voice_profiles import profile
    for gender in ('male','female'):
        raw=speech.synthesize('Ja, ich bin einunddreißig Jahre alt. Der Hund hat mich in den Arm gebissen. Ich bekomme normal Luft.','Anrufer',profile('smoke:'+gender,gender))
        with wave.open(io.BytesIO(raw),'rb') as wav:
            assert wav.getframerate()==(16000 if gender=='female' else 22050)
            assert 3<wav.getnframes()/wav.getframerate()<20
    assert set(speech.voices)=={'clear-model','female-model'}
    assert j['call']['voice_profile']['model'] in ('clear','female') and j['call']['voice_profile']['speaker_id']==0
    engine.db.close()
