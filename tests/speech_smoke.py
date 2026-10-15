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
        start=time.monotonic();raw=speech.synthesize(row['text'],row['speaker']);generated+=time.monotonic()-start
        assert raw.startswith(b'RIFF') and len(raw)>1000
        with wave.open(io.BytesIO(raw),'rb') as wav:
            assert wav.getnchannels()==1 and wav.getsampwidth()==2
            seconds=wav.getnframes()/wav.getframerate()
        rate=max(.8,min(1.7,seconds/max(.6,row['seconds']-.25)))
        played=seconds/rate+.25;duration+=played
        # Simulate the browser playing while later lines are prepared. This
        # measures end-to-end pacing, not only the sum of WAV durations.
        time.sleep(played)
        assert speech.synthesize(row['text'],row['speaker'])==raw
    elapsed=time.monotonic()-started
    assert 30<=duration<=50,(duration,generated)
    assert 30<=elapsed<=50,(elapsed,generated)
    print(json.dumps({'model':'de_DE-thorsten-high','lines':len(rows),'spoken_seconds':round(duration,2),'foreground_wait_seconds':round(generated,2),'conversation_elapsed_seconds':round(elapsed,2),'cache_entries':len(speech.cache)}))
    engine.db.close()
