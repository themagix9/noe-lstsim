"""Real WebAudio, HTTP line cursor and floating-window pause/resume in both engines.
The deterministic WAV stands in for neural synthesis; Docker smoke exercises Piper.
"""
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from playwright.sync_api import sync_playwright,expect
from browser_helpers import start_session,on_tab,choose_code

root=Path(__file__).resolve().parents[1]
out=io.BytesIO()
with wave.open(out,'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050)
    wav.writeframes(b'\0\0'*22050*3)
audio=out.getvalue()
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'0','CALL_AUTO':'1','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            for engine in (pw.chromium,pw.webkit):
                browser=engine.launch(headless=True);context=browser.new_context(viewport={'width':1440,'height':1000})
                context.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                requests=[]
                def speech(route):
                    requests.append(route.request.url)
                    route.fulfill(status=200,content_type='audio/wav',body=audio)
                context.route('**/api/call_audio?**',speech)
                page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                # Inspect actual filter graph construction, without replacing AudioContext.
                page.add_init_script("""window.phoneFilters=[];const make=AudioContext.prototype.createBiquadFilter;AudioContext.prototype.createBiquadFilter=function(){const node=make.call(this);phoneFilters.push(node);return node}""")
                page.goto('http://127.0.0.1:8080');page.get_by_label('Dein Disponentenname').fill('Sprachdisponent');page.locator('#lobby-submit').click();start_session(page)
                page.evaluate("command('generate',{kind:'emergency'})");expect(page.locator('#accept')).to_be_visible();page.locator('#accept').click()
                page.wait_for_function("document.getElementById('call-audio-status').textContent.includes('Sprachausgabe · LEO')",timeout=15000)
                job=page.evaluate('selected')
                page.locator('#call-continue').click();assert page.evaluate("detailTab==='disposition'")
                page.wait_for_function("state.jobs.find(j=>j.id===selected).call.transcript.length>=2",timeout=12000)
                page.wait_for_function("phoneFilters.some(n=>n.type==='highpass'&&n.frequency.value===300)&&phoneFilters.some(n=>n.type==='lowpass'&&n.frequency.value===3400)")
                page.locator('#close-dispatch').click()
                page.wait_for_function("id=>state.jobs.find(j=>j.id===id).call.paused",arg=job)
                count=page.evaluate("state.jobs.find(j=>j.id==='"+job+"').call.transcript.length")
                page.wait_for_timeout(3500)
                assert page.evaluate("state.jobs.find(j=>j.id==='"+job+"').call.transcript.length")==count
                fetched=len(requests)
                page.locator('[data-job="'+job+'"] .job-open').click()
                page.wait_for_function("id=>!state.jobs.find(j=>j.id===id).call.paused",arg=job)
                page.wait_for_function("n=>state.jobs.find(j=>j.id===selected).call.transcript.length>n",arg=count,timeout=12000)
                assert len(requests)<=fetched+1,'Reopening must not fetch/replay already spoken contributions'
                on_tab(page,'disposition');choose_code(page,'RD-17B1')
                row=page.locator('.resource-row').filter(has_text='77/002');row.locator('input').click();page.locator('#dispatch').click()
                expect(page.locator('#dispatch-dialog')).to_be_visible()
                assert page.evaluate("state.jobs.find(j=>j.id===selected).call.state==='connected'")
                page.wait_for_function("state.jobs.find(j=>j.id===selected).call.state==='ended'",timeout=50000)
                lines=page.evaluate("state.jobs.find(j=>j.id===selected).call.transcript")
                assert len(lines)==10 and 'Wir schicken jemanden' in lines[-2]['text']
                assert len(requests)==10,(len(requests),requests)
                assert not errors,errors
                browser.close();print(engine.name+': actual WebAudio, telephone filter, pause/resume without replay, early disposition and complete transcript passed.')
    finally:proc.terminate();proc.wait(timeout=5)
