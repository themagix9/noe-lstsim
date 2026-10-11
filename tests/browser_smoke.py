"""End-to-end multiplayer UI test, run separately with Playwright installed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            host=browser.new_context(viewport={'width':1440,'height':1100});guest=browser.new_context(viewport={'width':1280,'height':1000})
            a=host.new_page();b=guest.new_page();errors=[]
            a.on('pageerror',lambda e:errors.append(str(e)));b.on('pageerror',lambda e:errors.append(str(e)))
            # Never download OSM tiles in automated tests. Render a local placeholder instead.
            for context in (host,guest):context.route('https://tile.openstreetmap.org/**',lambda route:route.fulfill(status=200,content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#edf1ee"/></svg>'))
            a.goto('http://127.0.0.1:8080');a.locator('#mode-multi').click();a.get_by_label('Dein Disponentenname').fill('Disponent A');a.get_by_role('button',name='Sitzung erstellen',exact=True).click()
            expect(a.locator('#lobby')).to_be_hidden();code=a.locator('#copy-code').inner_text();assert len(code)==8
            b.goto('http://127.0.0.1:8080');b.locator('#mode-multi').click();b.get_by_role('button',name='Mit Code beitreten').click();b.get_by_label('Dein Disponentenname').fill('Disponent B');b.get_by_label('Sitzungscode',exact=True).fill(code);b.get_by_role('button',name='Sitzung beitreten',exact=True).click();expect(b.locator('#lobby')).to_be_hidden()
            expect(a.locator('#players')).to_contain_text('Disponent B',timeout=8000)
            a.get_by_role('button',name='+ Ereignis').click();a.get_by_role('button',name='Transportauftrag',exact=True).click();a.locator('.job').first.click();a.get_by_role('button',name='Einsatz übernehmen',exact=True).click()
            expect(b.locator('.job')).to_contain_text('Betreuung: Disponent A',timeout=8000)
            b.locator('.job').first.click();expect(b.locator('#dispatch')).to_be_disabled()
            a.get_by_role('button',name='Zur Übergabe freigeben').click();expect(b.locator('#claim')).to_be_visible(timeout=8000);b.locator('#claim').click();expect(a.locator('#detail')).to_contain_text('Betreuung: Disponent B',timeout=8000)
            b.locator('.dispatch-options input').first.check();b.locator('#dispatch').click();expect(b.locator('#detail')).to_contain_text('Alarmiert');b.locator('#close-dispatch').click();a.locator('#close-dispatch').click();expect(a.locator('#fleet-table')).to_contain_text('Alarmiert',timeout=8000)
            b.locator('#chat-input').fill('Transport übernommen.');b.get_by_role('button',name='Senden',exact=True).click();expect(a.locator('#chat')).to_contain_text('Transport übernommen.',timeout=8000)
            a.reload();expect(a.locator('#lobby')).to_be_hidden(timeout=8000);expect(a.locator('#copy-code')).to_have_text(code)
            a.get_by_role('button',name='Ressourcen',exact=True).click();expect(a.locator('#graphic-list img')).to_have_count(6);a.wait_for_function("[...document.querySelectorAll('#graphic-list img')].every(img=>img.complete&&img.naturalWidth>0)")
            a.get_by_role('button',name='Disposition',exact=True).click();a.locator('#speed').select_option('60');a.locator('#pause').click();expect(a.locator('#running')).to_have_text('SIMULATION LÄUFT')
            assert a.evaluate("document.documentElement.scrollHeight<=innerHeight && document.documentElement.scrollWidth<=innerWidth"),'Desktop app overflows viewport';assert a.evaluate("leafletMap.scrollWheelZoom.enabled()");assert a.evaluate("document.querySelectorAll('.resource-marker').length===state.vehicles.filter(relevant).filter(v=>v.status!=='ready').length"),'Parked resources rendered as vehicle markers';Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);a.screenshot(path='/tmp/noe-ui-qa/desktop.png',full_page=True)
            a.set_viewport_size({'width':390,'height':844});a.wait_for_timeout(200);assert a.evaluate("document.documentElement.scrollHeight<=innerHeight && document.documentElement.scrollWidth<=innerWidth"),'Mobile app overflows viewport';a.screenshot(path='/tmp/noe-ui-qa/mobile.png',full_page=True)
            assert not errors,errors
            # Validate a private session, manual AMPDS modal, reservation and a Vienna bed workflow.
            solo=browser.new_context(viewport={'width':1440,'height':1100});solo.route('https://tile.openstreetmap.org/**',lambda route:route.abort());c=solo.new_page();c.on('pageerror',lambda e:errors.append(str(e)));c.goto('http://127.0.0.1:8080');c.get_by_label('Dein Disponentenname').fill('Solo');c.locator('#lobby-submit').click();expect(c.locator('#lobby')).to_be_hidden();expect(c.locator('#copy-code')).to_be_hidden();expect(c.locator('#chat-panel')).to_be_hidden();c.locator('#create-manual').click();c.locator('#manual-kind').select_option('transport');c.get_by_label('Einsatzort / Adresse',exact=True).fill('Teststraße, Schwechat');c.locator('#manual-form button.primary').click();expect(c.locator('#dispatch-dialog')).to_be_visible();expect(c.locator('.resource-row').first).to_contain_text('km');c.locator('#reserve').click();expect(c.locator('#detail')).to_contain_text('Reserviert:');c.locator('#apply-aao').click();c.locator('#dispatch').click();expect(c.locator('#detail')).to_contain_text('Alarmiert');c.locator('#close-dispatch').click();
            c.locator('#demo').click();c.locator('#new-vienna').click();expect(c.locator('#dispatch-dialog')).to_be_visible(timeout=8000);c.locator('#accept').click();c.locator('#job-search').fill('RD-31D3');c.locator('#job-code').select_option('RD-31D3');c.locator('#job-code').focus();c.evaluate("window.stableSelect=document.getElementById('job-code')");c.wait_for_timeout(4200);assert c.evaluate("window.stableSelect===document.getElementById('job-code')"),'Polling replaced focused AMPDS selector';expect(c.locator('#detail')).to_contain_text('Einsatznummer');expect(c.locator('#detail')).to_contain_text('Verrechnungsnummer');expect(c.locator('#job-code')).to_have_value('RD-31D3');
            with c.expect_response(lambda response:response.url.endswith('/api/edit_job')) as edited:
                c.locator('#save-job').click()
            assert edited.value.ok,edited.value.text()
            expect(c.locator('#detail')).to_contain_text('ALS orange');c.locator('#apply-aao').click()
            with c.expect_response(lambda response:response.url.endswith('/api/dispatch')) as dispatched:
                c.locator('#dispatch').click()
            assert dispatched.value.ok,dispatched.value.text()
            expect(c.locator('#detail')).to_contain_text('Alarmiert');c.locator('#close-dispatch').click()
            with c.expect_response(lambda response:response.url.endswith('/api/control')):
                c.locator('#speed').select_option('60')
            with c.expect_response(lambda response:response.url.endswith('/api/control')):
                c.locator('#pause').click()
            expect(c.locator('#running')).to_have_text('SIMULATION LÄUFT')
            deadline=time.monotonic()+90
            while time.monotonic()<deadline and not c.locator('.job.emergency').filter(has_text='Wiener Ziel angefordert').count():
                if c.locator('#dispatch-dialog').is_visible():c.locator('#close-dispatch').click()
                c.wait_for_timeout(500)
            if c.locator('#dispatch-dialog').is_visible():c.locator('#close-dispatch').click()
            if not c.locator('.job.emergency').filter(has_text='Wiener Ziel angefordert').count():
                print('Vienna workflow diagnostic:',c.evaluate("({clock:state.clock,speed:state.speed,paused:state.paused,jobs:state.jobs.filter(j=>j.crew_target),vehicles:state.vehicles.filter(v=>v.job),toast:document.getElementById('toast').textContent})"),flush=True)
                c.screenshot(path='/tmp/noe-ui-qa/vienna-failure.png',full_page=True)
            expect(c.locator('.job.emergency').filter(has_text='Wiener Ziel angefordert').first).to_be_visible();c.locator('.job.emergency').filter(has_text='Wiener Ziel angefordert').first.click();c.locator('#bed-request').click();expect(c.locator('#send-sds')).to_be_visible(timeout=8000);c.locator('#send-sds').click();expect(c.locator('#detail')).to_contain_text('An Mannschaft übermittelt via SDS');c.screenshot(path='/tmp/noe-ui-qa/vienna-modal.png',full_page=True);
            c.locator('#close-dispatch').click();c.locator('#leave-room').click();c.screenshot(path='/tmp/noe-ui-qa/landing.png',full_page=True);assert not errors,errors
            print('Multiplayer browser test passed: join, roster, claim, handover, dispatch, chat, resume, graphics, clock.')
            browser.close()
    finally:proc.terminate();proc.wait(timeout=5)
