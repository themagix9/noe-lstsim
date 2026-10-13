"""Two distinct roles cooperate through the actual UI and live transcript."""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from browser_helpers import on_tab,choose_code,start_session

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'0','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport={'width':1440,'height':1100});dis=browser.new_context(viewport={'width':1440,'height':1100})
            for context in (ctx,dis):context.route('https://tile.openstreetmap.org/**',lambda r:r.abort())
            c=ctx.new_page();d=dis.new_page();errors=[]
            for page in (c,d):page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8080');page.locator('#mode-multi').click()
            c.get_by_label('Dein Disponentenname').fill('Anrufannahme');c.locator('#workflow-select').select_option('split');c.locator('#role-select').select_option('calltaker');c.locator('#lobby-submit').click();expect(c.locator('#lobby')).to_be_hidden();start_session(c);code=c.locator('#copy-code').inner_text()
            d.locator('#lobby-join-tab').click();d.get_by_label('Dein Disponentenname').fill('Disposition');d.get_by_label('Sitzungscode',exact=True).fill(code);d.locator('#role-select').select_option('dispatcher');d.locator('#lobby-submit').click();expect(d.locator('#lobby')).to_be_hidden();start_session(d)
            expect(c.locator('#mode-label')).to_have_text('CALLTAKER');expect(d.locator('#mode-label')).to_have_text('DISPONENT')
            c.locator('#demo').click();c.locator('#new-call').click();expect(c.locator('#accept')).to_be_visible();c.locator('#accept').click()
            expect(d.locator('.job.emergency')).to_contain_text('Abfrage läuft beim Calltaker');d.locator('.job.emergency').click();on_tab(d,'kommunikation');expect(d.locator('.call-dialogue')).to_contain_text('wo genau ist der Notfallort');expect(d.locator('#call-next')).to_be_disabled()
            for _ in range(6):
                with c.expect_response(lambda r:r.url.endswith('/api/call_question')) as response:c.locator('#call-next').click()
                assert response.value.ok,response.value.text()
            c.locator('#handoff-note').fill('Zugang über die Seitentür.');c.locator('#handoff-job').click();expect(c.locator('#dispatch-dialog')).to_be_hidden()
            expect(d.locator('.job.emergency')).to_contain_text('Bereit zur Disposition');expect(d.locator('#detail-panel-kommunikation')).to_contain_text('Zugang über die Seitentür.');expect(d.locator('.call-dialogue')).to_contain_text('Telefonat beendet')
            choose_code(d,'RD-17B1');on_tab(d,'disposition').locator('.resource-row').filter(has_text='77/002').locator('input').check()
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);d.screenshot(path='/tmp/noe-ui-qa/split-disposition.png');c.screenshot(path='/tmp/noe-ui-qa/split-calltaker.png')
            d.locator('#dispatch').click();expect(d.locator('#dispatch-dialog')).to_be_hidden();expect(c.locator('#fleet-table')).to_contain_text('Alarmiert')
            denied=c.evaluate("fetch('/api/dispatch',{method:'POST',headers:authHeaders(),body:JSON.stringify({job:state.jobs.at(-1).id,vehicles:[]})}).then(r=>r.status)");assert denied==403
            assert not errors,errors;browser.close();print('Split multiplayer: live transcript, role restrictions, handoff note and dispatcher booking passed.')
    finally:proc.terminate();proc.wait(timeout=5)
