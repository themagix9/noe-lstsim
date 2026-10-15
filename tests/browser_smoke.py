"""End-to-end multiplayer UI test, run separately with Playwright installed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
from browser_helpers import on_tab, choose_code, start_session, wait_for_auto_call

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'RADIO_INTERVAL':'0','ROUTING_ENABLED':'0','REINFORCEMENTS_AUTO':'0'},stdout=subprocess.DEVNULL)
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
            expect(a.locator('#lobby')).to_be_hidden();start_session(a);code=a.locator('#copy-code').inner_text();assert len(code)==8
            b.goto('http://127.0.0.1:8080');b.locator('#mode-multi').click();b.get_by_role('button',name='Mit Code beitreten').click();b.get_by_label('Dein Disponentenname').fill('Disponent B');b.get_by_label('Sitzungscode',exact=True).fill(code);b.get_by_role('button',name='Sitzung beitreten',exact=True).click();expect(b.locator('#lobby')).to_be_hidden();start_session(b)
            expect(a.locator('#players')).to_contain_text('Disponent B',timeout=8000)
            a.get_by_role('button',name='+ Ereignis').click();a.get_by_role('button',name='Transportauftrag',exact=True).click();a.locator('.job').first.click();a.get_by_role('button',name='Einsatz übernehmen',exact=True).click()
            expect(b.locator('.job')).to_contain_text('Betreuung: Disponent A',timeout=8000)
            b.locator('.job').first.click();expect(b.locator('#dispatch')).to_be_disabled()
            a.get_by_role('button',name='Zur Übergabe freigeben').click();expect(b.locator('#claim')).to_be_visible(timeout=8000);b.locator('#claim').click();expect(a.locator('#detail')).to_contain_text('Betreuung: Disponent B',timeout=8000)
            choose_code(b, 'KTR-90K3');on_tab(b, 'disposition').locator('.dispatch-options input').first.check();b.locator('#dispatch').click();expect(b.locator('#detail')).to_contain_text('Alarmiert');expect(b.locator('#dispatch-dialog')).not_to_be_visible();a.locator('#close-dispatch').click();expect(a.locator('#fleet-table')).to_contain_text('Alarmiert',timeout=8000)
            b.locator('#chat-input').fill('Transport übernommen.');b.get_by_role('button',name='Senden',exact=True).click();expect(a.locator('#chat')).to_contain_text('Transport übernommen.',timeout=8000)
            a.reload();expect(a.locator('#lobby')).to_be_hidden(timeout=8000);expect(a.locator('#copy-code')).to_have_text(code)
            # Both see an incoming offer; claiming it closes only the other prompt.
            a.evaluate("command('generate',{kind:'emergency'})")
            expect(a.locator('#accept')).to_be_visible();expect(b.locator('#accept')).to_be_visible()
            a.locator('#accept').click()
            expect(b.locator('#dispatch-dialog')).not_to_be_visible()
            expect(b.locator('#toast')).to_have_text('Benutzer Disponent A hat den Einsatz übernommen.')
            expect(a.locator('#dispatch-dialog')).to_be_visible()
            wait_for_auto_call(a)
            a.locator('#close-dispatch').click()
            a.locator('#desk-menu > summary').click();a.get_by_role('button',name='Ressourcen',exact=True).click();expect(a.locator('#graphic-list img')).to_have_count(10);a.wait_for_function("[...document.querySelectorAll('#graphic-list img')].every(img=>img.complete&&img.naturalWidth>0)")
            a.locator('#desk-menu > summary').click();a.get_by_role('button',name='Disposition',exact=True).click();a.locator('#speed').select_option('60');a.locator('#pause').click();expect(a.locator('#running')).to_have_text('SIMULATION LÄUFT')
            # Move and resize a desk window, preserve its layout through live updates and reload.
            a.evaluate("command('control',{paused:true})")
            panel=a.locator('#window-resources');before=panel.bounding_box();head=panel.locator('.panel-head').bounding_box()
            a.mouse.move(head['x']+70,head['y']+12);a.mouse.down();a.mouse.move(head['x']-80,head['y']+37,steps=5);a.mouse.up();moved=panel.bounding_box();assert moved['x']<before['x']-100,(before,moved)
            handle=panel.locator('.window-resize').bounding_box();a.mouse.move(handle['x']+14,handle['y']+14);a.mouse.down();a.mouse.move(handle['x']+54,handle['y']+44,steps=5);a.mouse.up();resized=panel.bounding_box();assert resized['width']>moved['width']+20,(moved,resized)
            a.wait_for_timeout(1500);assert abs(panel.bounding_box()['x']-resized['x'])<2
            a.reload();expect(a.locator('#lobby')).to_be_hidden();expect(panel).to_be_visible();assert abs(panel.bounding_box()['width']-resized['width'])<3
            a.locator('#desk-menu > summary').click();a.locator('#reset-layout').click();assert a.locator('#map').bounding_box()['height']>400
            a.locator('#pause').click();expect(a.locator('#running')).to_have_text('SIMULATION LÄUFT')
            assert a.evaluate("document.documentElement.scrollHeight<=innerHeight && document.documentElement.scrollWidth<=innerWidth"),'Desktop app overflows viewport';assert a.evaluate("leafletMap.scrollWheelZoom.enabled()");assert a.evaluate("document.querySelectorAll('.resource-marker:not(.agency-marker)').length===state.vehicles.filter(relevant).filter(mapVisible).length"),'Parked or idle FR resources rendered as vehicle markers';assert a.evaluate("state.vehicles.filter(v=>v.type==='FR'&&v.status==='fr_ready').every(v=>!mapObjects.has('vehicle:'+v.id))");assert a.evaluate("resourceName(state.vehicles.find(v=>v.station==='c3'))==='99/003 Christophorus 3' && homeLabel(state.vehicles.find(v=>v.station==='schwechat'))==='SW'");Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);a.screenshot(path='/tmp/noe-ui-qa/desktop.png',full_page=True)
            a.set_viewport_size({'width':1366,'height':768});a.wait_for_timeout(200);assert a.evaluate("document.documentElement.scrollHeight<=innerHeight && document.documentElement.scrollWidth<=innerWidth && document.getElementById('map').clientHeight>=90"),'Laptop layout does not fit';a.screenshot(path='/tmp/noe-ui-qa/laptop.png',full_page=True);a.set_viewport_size({'width':390,'height':844});a.wait_for_timeout(200);assert a.evaluate("document.documentElement.scrollHeight<=innerHeight && document.documentElement.scrollWidth<=innerWidth"),'Mobile app overflows viewport';a.screenshot(path='/tmp/noe-ui-qa/mobile.png',full_page=True)
            assert not errors,errors
            # Validate a private session, manual AMPDS modal, reservation and a Vienna bed workflow.
            solo=browser.new_context(viewport={'width':1440,'height':1100});solo.route('https://tile.openstreetmap.org/**',lambda route:route.abort());c=solo.new_page();c.on('pageerror',lambda e:errors.append(str(e)));c.goto('http://127.0.0.1:8080');c.get_by_label('Dein Disponentenname').fill('Solo');c.locator('#lobby-submit').click();expect(c.locator('#lobby')).to_be_hidden();start_session(c);expect(c.locator('#copy-code')).to_be_hidden();expect(c.locator('#chat-panel')).to_be_hidden();c.locator('#create-manual').click();c.locator('#manual-kind').select_option('transport');expect(c.locator('#manual-code')).to_have_value('');c.locator('#manual-code').select_option('KTR-90K3');c.get_by_label('Einsatzort / Adresse',exact=True).fill('Teststraße, Schwechat');c.locator('#manual-form button.primary').click();expect(c.locator('#dispatch-dialog')).to_be_visible();expect(on_tab(c, 'disposition').locator('.resource-row').first).to_contain_text('km');expect(on_tab(c, 'disposition').locator('#reserve')).to_be_disabled();c.locator('#reserve-vehicle').select_option(c.evaluate("[...document.querySelector('#reserve-vehicle').options].find(o=>o.value&&!o.disabled).value"));expect(c.locator('#reserve')).to_be_enabled();c.locator('#reserve').click();expect(c.locator('#detail')).to_contain_text('Reserviert:');on_tab(c, 'disposition').locator('#apply-aao').click();c.locator('#dispatch').click();expect(c.locator('#dispatch-dialog')).not_to_be_visible();
            c.locator('#demo').click();c.locator('#new-vienna').click();expect(c.locator('#dispatch-dialog')).to_be_visible(timeout=8000);c.locator('#accept').click();
            wait_for_auto_call(c)
            c.locator('#call-continue').click()
            on_tab(c, 'disposition').locator('#job-search').fill('RD-31D3');choose_code(c, 'RD-31D3');on_tab(c, 'disposition').locator('#job-code').focus();c.evaluate("window.stableSelect=document.getElementById('job-code')");c.wait_for_timeout(4200);assert c.evaluate("window.stableSelect===document.getElementById('job-code')"),'Polling replaced focused AMPDS selector';expect(c.locator('#detail')).to_contain_text('Einsatznummer');expect(c.locator('#detail')).to_contain_text('Verrechnungsnummer');expect(on_tab(c, 'disposition').locator('#job-code')).to_have_value('RD-31D3');
            with c.expect_response(lambda response:response.url.endswith('/api/edit_job')) as edited:
                c.locator('#save-job').click()
            assert edited.value.ok,edited.value.text()
            expect(c.locator('#detail')).to_contain_text('ALS orange');on_tab(c, 'disposition').locator('#apply-aao').click()
            with c.expect_response(lambda response:response.url.endswith('/api/dispatch')) as dispatched:
                c.locator('#dispatch').click()
            assert dispatched.value.ok,dispatched.value.text()
            expect(c.locator('#dispatch-dialog')).not_to_be_visible()
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
            expect(c.locator('.job.emergency').filter(has_text='Wiener Ziel angefordert').first).to_be_visible()
            expect(c.locator('#vienna-alerts')).to_contain_text('Wiener Ziel – Kasusnummer erforderlich')
            c.locator('#tab-transport').click();expect(c.locator('#vienna-alerts')).to_be_visible()
            c.locator('#vienna-alerts [data-vienna-job]').first.evaluate('e=>{window.viennaButton=e;e.focus()}')
            c.evaluate('ViennaAlerts.render({...state,clock:state.clock+61})')
            assert c.evaluate('viennaButton.isConnected&&document.activeElement===viennaButton')
            c.locator('#vienna-alerts [data-vienna-job]').first.click()
            expect(c.locator('#detail-panel-transport')).to_be_visible();c.locator('#bed-request').click()
            expect(c.locator('#send-sds')).to_be_visible(timeout=8000)
            expect(c.locator('#vienna-alerts')).to_contain_text('Kasusnummer liegt vor – an Mannschaft senden')
            c.locator('#send-sds').click();expect(c.locator('#vienna-alerts')).to_be_hidden()
            expect(c.locator('#detail')).to_contain_text('An Mannschaft übermittelt via SDS');c.screenshot(path='/tmp/noe-ui-qa/vienna-modal.png',full_page=True);
            c.locator('#close-dispatch').click();c.get_by_role('button',name='Zur Startseite',exact=True).click();expect(c.locator('#lobby')).to_be_visible();expect(c.locator('#dispatch-dialog')).not_to_be_visible();c.locator('#resume').click();expect(c.locator('#lobby')).to_be_hidden();expect(c.locator('#running')).to_have_text('SIMULATION PAUSIERT');
            if c.locator('#dispatch-dialog').is_visible():c.locator('#close-dispatch').click()
            c.get_by_role('button',name='Zur Startseite',exact=True).click();expect(c.locator('#lobby')).to_be_visible();c.screenshot(path='/tmp/noe-ui-qa/landing.png',full_page=True);assert not errors,errors
            # A fresh private crew requests a NEF interactively; dispatch is a real server action.
            radio_context=browser.new_context(viewport={'width':1440,'height':1000});radio_context.route('https://tile.openstreetmap.org/**',lambda route:route.abort());d=radio_context.new_page();d.on('pageerror',lambda e:errors.append(str(e)));d.goto('http://127.0.0.1:8080');d.get_by_label('Dein Disponentenname').fill('Funkdisponent');d.locator('#lobby-submit').click();expect(d.locator('#lobby')).to_be_hidden();start_session(d);d.locator('#create-manual').click();expect(d.locator('#manual-code')).to_have_value('');d.locator('#manual-code').select_option('RD-1A1');d.get_by_label('Einsatzort / Adresse',exact=True).fill('Bruck Hainburger-Straße 27, 2320 Schwechat');d.get_by_label('Breitengrad',exact=True).fill('48.14');d.get_by_label('Längengrad',exact=True).fill('16.4866');d.locator('#manual-form button.primary').click();on_tab(d, 'disposition').locator('.resource-row').filter(has_text='77/002').locator('input').check();d.locator('#dispatch').click();expect(d.locator('#dispatch-dialog')).not_to_be_visible();d.locator('#speed').select_option('60');d.locator('#pause').click();d.wait_for_function("state.vehicles.some(v=>v.callsign==='77/002'&&v.status==='scene')",timeout=15000);d.wait_for_function("state.jobs.find(j=>j.id===state.vehicles.find(v=>v.callsign==='77/002').job).patient_condition.reported",timeout=10000);d.evaluate("command('control',{paused:true})");
            if d.locator('#dispatch-dialog').is_visible():d.locator('#close-dispatch').click()
            d.evaluate("command('radio_generate',{job:state.vehicles.find(v=>v.callsign==='77/002').job,vehicle:state.vehicles.find(v=>v.callsign==='77/002').id,kind:'NEF',reason:'Laufende Reanimation.'})")
            radio_id=d.evaluate("state.radio_calls.find(c=>c.vehicle===state.vehicles.find(v=>v.callsign==='77/002').id&&c.kind==='NEF'&&c.state==='calling').id")
            call=d.locator('#radio-queue .radio-call').filter(has=d.locator('[data-radio="'+radio_id+'"]'))
            d.locator('#radio-queue [data-radio="'+radio_id+'"][data-step=listen]').click()
            d.locator('#radio-queue [data-radio="'+radio_id+'"][data-step=reason]').click()
            expect(call).to_contain_text('Laufende Reanimation.');expect(d.locator('#radio-queue [data-radio="'+radio_id+'"][data-step=confirm]')).to_be_disabled()
            call.get_by_role('button',name='Einsatz öffnen',exact=True).click()
            on_tab(d,'disposition').locator('.resource-row').filter(has_text='77/099').locator('input').check();d.locator('#dispatch').click()
            d.locator('#radio-queue [data-radio="'+radio_id+'"][data-step=confirm]').click()
            expect(d.locator('#logs')).to_contain_text('NEF Schwechat kommt ab Wache.');expect(d.locator('#logs')).to_contain_text('LEO Ende.')
            d.screenshot(path='/tmp/noe-ui-qa/radio-complete.png',full_page=True);assert not errors,errors
            print('Multiplayer browser test passed: join, roster, claim, handover, dispatch, chat, resume, graphics, clock.')
            browser.close()
    finally:proc.terminate();proc.wait(timeout=5)
