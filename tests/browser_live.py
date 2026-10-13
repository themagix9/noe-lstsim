"""Live stream, stable editing, empty code choices, filters and sorting."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect
from browser_helpers import on_tab, choose_code, start_session

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'0','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1100})
            context.route('https://tile.openstreetmap.org/**',lambda r:r.abort());p=context.new_page();errors=[];requests=[]
            p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:requests.append(r.url));p.goto('http://127.0.0.1:8080');p.get_by_label('Dein Disponentenname').fill('Livetest');p.locator('#lobby-submit').click();expect(p.locator('#lobby')).to_be_hidden();start_session(p)
            p.locator('#pause').click();p.locator('#create-manual').click();expect(p.locator('#manual-code')).to_have_value('')
            p.get_by_label('Einsatzort / Adresse',exact=True).fill('Schwechat Testadresse');p.locator('#manual-form button.primary').click();expect(p.locator('#manual-dialog')).to_be_visible();assert p.evaluate('state.jobs.length')==0
            p.locator('#manual-code').select_option('RD-1A1');p.locator('#manual-form button.primary').click();expect(p.locator('#dispatch-dialog')).to_be_visible()
            on_tab(p, 'einsatz').locator('#job-additional').focus();p.evaluate("window.stableText=document.getElementById('job-additional')")
            on_tab(p, 'einsatz').locator('#job-additional').press_sequentially('Text bleibt erhalten',delay=200)
            assert p.evaluate("stableText===document.getElementById('job-additional')&&document.activeElement===stableText")
            expect(on_tab(p, 'einsatz').locator('#job-additional')).to_have_value('Text bleibt erhalten')
            on_tab(p, 'disposition').locator('[data-filter="RTW"]').click();assert p.evaluate("[...document.querySelectorAll('.resource-row')].every(e=>['RTW','RTW-C'].includes(state.vehicles.find(v=>v.id===e.dataset.resourceId).type))")
            row=on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002');expect(row).to_contain_text('RTW 77/002');row.locator('input').check();on_tab(p, 'einsatz');expect(p.locator('#detail-panel-disposition')).to_be_hidden();expect(p.locator('#job-additional')).to_have_value('Text bleibt erhalten');on_tab(p, 'disposition');expect(row.locator('input')).to_be_checked()
            on_tab(p, 'disposition').locator('[data-filter="NA"]').click();expect(on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002')).to_have_count(0)
            on_tab(p, 'disposition').locator('[data-filter="RTW"]').click();expect(on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002').locator('input')).to_be_checked()
            on_tab(p, 'disposition').locator('#resource-sort').select_option('callsign');on_tab(p, 'disposition').locator('#resource-direction').select_option('desc')
            assert p.evaluate("(()=>{const rows=[...document.querySelectorAll('.resource-row')].map(e=>state.vehicles.find(v=>v.id===e.dataset.resourceId));return rows.every((v,i)=>!i||rows[i-1].callsign.localeCompare(v.callsign,'de',{numeric:true})>=0)})()")
            expect(on_tab(p, 'einsatz').locator('#job-additional')).to_have_value('Text bleibt erhalten');p.locator('#close-dispatch').click()
            # UI clock interpolates without fetching /api/state every two seconds.
            start=p.locator('#clock').inner_text();p.wait_for_timeout(1200);assert p.locator('#clock').inner_text()!=start
            p.locator('#pause').click();expect(p.locator('#running')).to_have_text('SIMULATION PAUSIERT');start=p.locator('#clock').inner_text();p.wait_for_timeout(1300);expect(p.locator('#clock')).to_have_text(start)
            p.locator('#create-manual').click();p.locator('#manual-kind').select_option('transport');expect(p.locator('#manual-code')).to_have_value('');p.locator('#manual-search').fill('Dialyse');expect(p.locator('#manual-code option[value="KTR-93Y2"]')).to_have_count(1);p.locator('#manual-code').select_option('KTR-93Y2');p.get_by_label('Einsatzort / Adresse',exact=True).fill('Transportadresse Schwechat');p.locator('#manual-form button.primary').click()
            expect(p.locator('#detail')).to_contain_text('Abholzeit');assert on_tab(p, 'einsatz').locator('#job-pickup').get_attribute('step')=='1800';expect(p.locator('.job.transport .pickup-time.urgent')).to_be_visible();on_tab(p, 'disposition').locator('[data-filter="KTW"]').click();assert p.evaluate("[...document.querySelectorAll('.resource-row')].every(e=>['KTW','KTW-B','BKTW'].includes(state.vehicles.find(v=>v.id===e.dataset.resourceId).type))")
            on_tab(p, 'disposition').locator('#resource-sort').select_option('status');on_tab(p, 'disposition').locator('#resource-direction').select_option('asc');p.wait_for_timeout(1500);expect(on_tab(p, 'disposition').locator('#resource-sort')).to_have_value('status');expect(p.locator('#manual-dialog')).not_to_be_visible()
            # Actual browser audio graph: three bell partials, once despite live updates.
            p.evaluate("window.gongTones=0;const original=AudioContext.prototype.createOscillator;AudioContext.prototype.createOscillator=function(){window.gongTones++;return original.call(this)}")
            p.locator('#close-dispatch').click();p.locator('#pause').click();p.wait_for_function('window.gongTones===3');p.wait_for_timeout(1200);assert p.evaluate('window.gongTones')==3
            p.locator('#pause').click()
            assert not any(u.endswith('/api/state') for u in requests),requests;assert not errors,errors
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path='/tmp/noe-ui-qa/live-filter-sort.png');browser.close();print('Live editing, empty code, clock, filter, sort and preserved selection browser tests passed.')
    finally:proc.terminate();proc.wait(timeout=5)
