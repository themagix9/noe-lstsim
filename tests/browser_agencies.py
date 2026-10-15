"""Police/fire, dispatch from radio, text editing, map focus and real speech gaps."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect
from browser_helpers import on_tab,start_session,choose_code

def visible(page, selector):
    target=page.locator(selector)
    target.first.wait_for(state='attached')
    panel=page.locator('[role="tabpanel"]:not([hidden])')
    for _ in range(12):
        if target.first.is_visible():return target
        previous=panel.get_by_role('button',name='Vorige Seite',exact=True)
        if previous.count() and previous.is_enabled():previous.click()
        else:break
    for _ in range(12):
        if target.first.is_visible():return target
        following=panel.get_by_role('button',name='Nächste Seite',exact=True)
        if following.count() and following.is_enabled():following.click()
        else:break
    expect(target.first).to_be_visible()
    return target

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'RADIO_INTERVAL':'2','ROUTING_ENABLED':'0','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1100});context.route('https://tile.openstreetmap.org/**',lambda r:r.abort())
            p=context.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto('http://127.0.0.1:8080');p.get_by_label('Dein Disponentenname').fill('Behörden-Test');p.locator('#lobby-submit').click();expect(p.locator('#lobby')).to_be_hidden();start_session(p)
            p.locator('#create-manual').click();p.locator('#manual-code').select_option('RD-1A1');p.get_by_label('Einsatzort / Adresse',exact=True).fill('Übungsadresse Schwechat');p.get_by_label('Breitengrad',exact=True).fill('48.142');p.get_by_label('Längengrad',exact=True).fill('16.480');p.locator('#manual-form button.primary').click();expect(p.locator('#dispatch-dialog')).to_be_visible()
            p.evaluate("async()=>{window.jobId=selected;window.unitId=state.vehicles.find(v=>v.callsign==='77/002').id;await command('vehicle_status',{vehicle:unitId,status:'6'});await command('dispatch',{job:jobId,vehicles:[unitId]});}")
            p.wait_for_function("state.vehicles.find(v=>v.id===unitId).status==='assigned'&&mapObjects.has('vehicle:'+unitId)")
            p.evaluate("command('vehicle_status',{vehicle:unitId,status:'9'})");p.wait_for_function("state.vehicles.find(v=>v.id===unitId).status==='acknowledged'&&mapObjects.has('vehicle:'+unitId)")
            on_tab(p,'einsatz');p.locator('#job-additional').fill('Zugang über den Innenhof');p.locator('#save-job-additional').click();p.wait_for_function("state.jobs.find(j=>j.id===jobId).additional==='Zugang über den Innenhof'")
            assert p.evaluate("['SDS','ESApp'].every(channel=>state.messages.some(m=>m.job===jobId&&m.channel===channel&&m.text.startsWith('EINSATZUPDATE')))")
            p.locator('#close-dispatch').click();expect(p.locator('.job-additional')).to_have_text('Zugang über den Innenhof');expect(p.locator('.job-expanded')).not_to_be_visible()
            p.locator('[data-focus-job]').click();expect(p.locator('#dispatch-dialog')).not_to_be_visible();assert p.evaluate("leafletMap.getZoom()===14&&Math.abs(leafletMap.getCenter().lat-state.jobs.find(j=>j.id===jobId).lat)<.0001")
            p.evaluate("openDispatch(jobId)");on_tab(p,'behoerden');p.locator('#agency-task-police').select_option('safety');p.locator('[data-agency-request=police]').click();p.wait_for_function("state.jobs.find(j=>j.id===jobId).agency_requests?.some(r=>r.kind==='police')");visible(p,'#agency-task-fire').select_option('extrication');visible(p,'[data-agency-request=fire]').click()
            p.wait_for_function("state.jobs.find(j=>j.id===jobId).agency_requests?.length===2");assert p.evaluate("state.agency_units.filter(v=>v.job===jobId).length===2")
            on_tab(p,'gebucht');expect(p.locator('#detail .agency-resource')).to_have_count(2);expect(p.locator('#detail .agency-resource').first).to_contain_text('Alarmiert / Ausrücken');on_tab(p,'behoerden')
            p.screenshot(path='/tmp/noe-ui-qa/agency-requests.png')
            p.evaluate("async()=>{await command('dispatch',{job:jobId,vehicles:[state.vehicles.find(v=>v.callsign==='64/007').id]});await command('vehicle_status',{vehicle:unitId,status:'2'});await command('control',{paused:false,speed:60})}")
            p.wait_for_function("state.vehicles.find(v=>v.id===unitId).status==='scene'",timeout=20000)
            p.evaluate("command('control',{paused:true})");assert p.evaluate("state.jobs.find(j=>j.id===jobId).agency_requirements.safety.cleared===false")
            assert not p.evaluate("state.jobs.find(j=>j.id===jobId).patient_condition.reported")
            p.evaluate("command('control',{paused:false,speed:60})")
            p.wait_for_function("state.jobs.find(j=>j.id===jobId).agency_requests.every(r=>r.task_completed!=null)",timeout=25000)
            p.wait_for_function("state.jobs.find(j=>j.id===jobId).patient_condition.reported",timeout=10000);p.evaluate("command('control',{paused:true})")
            on_tab(p,'gebucht');expect(p.locator('#detail .agency-resource')).to_have_count(2);expect(p.locator('#detail .agency-resource').first).to_contain_text('Am Einsatzort')
            on_tab(p,'kommunikation');p.wait_for_function("!state.radio_pending?.length",timeout=20000)
            before=time.monotonic();visible(p,'#radio-detail [data-radio][data-step=listen]').click()
            p.wait_for_function("state.radio_calls.some(c=>c.job===jobId&&c.kind==='Lagemeldung'&&c.state==='awaiting_end')")
            # The reply is queued, not inserted together with LEO's answer.
            assert p.evaluate("state.radio_pending.some(r=>r.text.startsWith('LEO von 77/002,'))")
            p.wait_for_function("!state.radio_pending.length",timeout=10000);assert time.monotonic()-before>=1.8
            expect(p.locator('#radio-detail')).to_contain_text('Weitere anfahrende Kräfte können storniert werden.')
            checkbox=visible(p,'#radio-detail [data-lage-unit]');expect(checkbox).to_have_count(1);checkbox.check();p.wait_for_timeout(1200);expect(checkbox).to_be_checked()
            visible(p,'#radio-detail [data-lage-storno]').click();p.wait_for_function("state.vehicles.find(v=>v.callsign==='64/007').job===null")
            p.wait_for_function("!state.radio_pending.length",timeout=30000);visible(p,'#radio-detail [data-radio][data-step=end]').click();p.wait_for_function("state.radio_calls.filter(c=>c.job===jobId&&c.kind==='Lagemeldung').every(c=>c.state==='closed')");p.wait_for_function("!state.radio_pending.length",timeout=10000)
            expect(p.locator('#logs')).to_contain_text('77/002 von LEO, verstanden. Ende.');p.screenshot(path='/tmp/noe-ui-qa/paced-scene-report.png')
            colors=p.evaluate("""()=>{const result={};for(const status of ['ready','radio','enroute','scene','transport','hospital','assigned']){const el=document.createElement('span');el.className='badge '+status;document.body.append(el);const css=getComputedStyle(el);result[status]=[css.backgroundColor,css.color];el.remove()}return result}""")
            assert colors['assigned']==['rgb(255, 255, 255)','rgb(207, 38, 56)'];assert colors['scene'][0]=='rgb(207, 52, 62)';assert colors['ready'][0]!=colors['radio'][0]
            p.set_viewport_size({'width':1366,'height':768});on_tab(p,'behoerden');p.wait_for_timeout(300);assert p.evaluate("document.getElementById('detail').scrollHeight<=document.getElementById('detail').clientHeight+1")
            choose_code(p,'RD-9E1');on_tab(p,'gebucht');expect(p.locator('#detail [data-ecpr-team=alarmed]')).to_contain_text('eCPR AKH alarmiert')
            p.evaluate("async()=>{await command('generate',{kind:'transport'});openDispatch(state.jobs.at(-1).id)}");on_tab(p,'disposition');assert p.locator('#job-code').input_value().startswith('KTR-');assert p.evaluate("state.jobs.at(-1).code_confirmed===true")
            assert not errors,errors;browser.close();print('Agency dispatch, live additional text, map focus, radio-origin alarm visibility, status colours and 2-second scene radio passed.')
    finally:proc.terminate();proc.wait(timeout=5)
