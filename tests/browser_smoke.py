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
            a.goto('http://127.0.0.1:8080');a.get_by_label('Dein Disponentenname').fill('Disponent A');a.get_by_role('button',name='Sitzung erstellen',exact=True).click()
            expect(a.locator('#lobby')).to_be_hidden();code=a.locator('#copy-code').inner_text();assert len(code)==8
            b.goto('http://127.0.0.1:8080');b.get_by_role('button',name='Mit Code beitreten').click();b.get_by_label('Dein Disponentenname').fill('Disponent B');b.get_by_label('Sitzungscode',exact=True).fill(code);b.get_by_role('button',name='Sitzung beitreten',exact=True).click();expect(b.locator('#lobby')).to_be_hidden()
            expect(a.locator('#players')).to_contain_text('Disponent B',timeout=8000)
            a.get_by_role('button',name='+ Ereignis').click();a.get_by_role('button',name='Transportauftrag',exact=True).click();a.locator('.job').first.click();a.get_by_role('button',name='Einsatz übernehmen',exact=True).click()
            expect(b.locator('.job')).to_contain_text('Betreuung: Disponent A',timeout=8000)
            b.locator('.job').first.click();expect(b.locator('#dispatch')).to_be_disabled()
            a.get_by_role('button',name='Zur Übergabe freigeben').click();expect(b.locator('#claim')).to_be_visible(timeout=8000);b.locator('#claim').click();expect(a.locator('#detail')).to_contain_text('Betreuung: Disponent B',timeout=8000)
            b.locator('.dispatch-options input').first.check();b.locator('#dispatch').click();expect(a.locator('#fleet-table')).to_contain_text('Alarmiert',timeout=8000)
            b.locator('#chat-input').fill('Transport übernommen.');b.get_by_role('button',name='Senden',exact=True).click();expect(a.locator('#chat')).to_contain_text('Transport übernommen.',timeout=8000)
            a.reload();expect(a.locator('#lobby')).to_be_hidden(timeout=8000);expect(a.locator('#copy-code')).to_have_text(code)
            a.get_by_role('button',name='Ressourcen',exact=True).click();expect(a.locator('#graphic-list img')).to_have_count(4);a.wait_for_function("[...document.querySelectorAll('#graphic-list img')].every(img=>img.complete&&img.naturalWidth>0)")
            a.get_by_role('button',name='Disposition',exact=True).click();a.locator('#speed').select_option('60');a.locator('#pause').click();expect(a.locator('#running')).to_have_text('SIMULATION LÄUFT')
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);a.screenshot(path='/tmp/noe-ui-qa/desktop.png',full_page=True)
            a.set_viewport_size({'width':390,'height':844});a.screenshot(path='/tmp/noe-ui-qa/mobile.png',full_page=True)
            assert not errors,errors
            print('Multiplayer browser test passed: join, roster, claim, handover, dispatch, chat, resume, graphics, clock.')
            browser.close()
    finally:proc.terminate();proc.wait(timeout=5)
