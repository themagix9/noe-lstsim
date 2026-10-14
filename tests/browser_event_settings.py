"""Live settings preserve typed rates, share persistence, and disable automatic KTs."""
import os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from browser_helpers import start_session
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'0','RADIO_INTERVAL':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000})
            page.route('https://tile.openstreetmap.org/**',lambda r:r.abort());errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:8080');page.get_by_label('Dein Disponentenname').fill('Frequenz-Test');page.locator('#lobby-submit').click();expect(page.locator('#lobby')).to_be_hidden();start_session(page)
            page.locator('#desk-menu').evaluate('e=>e.open=true');page.locator('[data-view=settings]').click()
            page.locator('#emergency-rate').fill('7.5');page.locator('#transport-rate').fill('2');page.wait_for_timeout(1300)
            expect(page.locator('#emergency-rate')).to_have_value('7.5');page.locator('#only-emergencies').click()
            page.wait_for_function("state.event_settings.emergency_per_hour===7.5&&!state.event_settings.transports_enabled")
            expect(page.locator('#transport-rate')).to_be_disabled()
            page.reload();page.wait_for_function('state?.session');page.locator('#desk-menu').evaluate('e=>e.open=true');page.locator('[data-view=settings]').click()
            expect(page.locator('#emergency-rate')).to_have_value('7.5');expect(page.locator('#transports-enabled')).not_to_be_checked()
            page.evaluate("async()=>{await command('generate',{kind:'transport'});await command('control',{speed:60,paused:false})}")
            page.wait_for_function("state.clock>=8*3600+240",timeout=12000);page.evaluate("command('control',{paused:true})")
            assert page.evaluate("state.jobs.filter(j=>j.kind==='transport').length===1")
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);page.screenshot(path='/tmp/noe-ui-qa/event-frequency.png');assert not errors,errors;browser.close()
            print('Live event-rate drafts, emergency-only preset, persistence and disabled automatic KTs passed.')
    finally:proc.terminate();proc.wait(timeout=5)
