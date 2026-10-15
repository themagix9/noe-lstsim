"""Shared UI for crew-requested telephone advice and a dispatcher-denied heli."""
import json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from browser_helpers import on_tab,start_session
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'app'))
os.environ['ROUTING_ENABLED']='0';os.environ['RADIO_INTERVAL']='0'
from sessions import Sessions
from engine import SCENARIOS

with tempfile.TemporaryDirectory() as data:
    sessions=Sessions(str(Path(data)/'simulation.sqlite3'))
    auth=sessions.create({'name':'TNA Disponent','mode':'multi'});member=sessions.member(auth['token']);engine=sessions.engine(member['room_id'])
    code=sessions.snapshot(member)['session']['code'];guest=sessions.join({'name':'Beobachter','code':code})
    def scene(callsign,score):
        j=engine.new_job('emergency',scenario=SCENARIOS[1]);v=next(v for v in engine.state['vehicles'] if v['callsign']==callsign)
        j.pop('call',None);j.update(accepted=True,asked=True,code_confirmed=True,status='scene',scene_report={'text':'Patient braucht weitere ärztliche Einschätzung.'},vehicles=[v['id']])
        j['patient_condition'].update(percent=score,reported=True,notarzt_required=score<45)
        v.update(job=j['id'],status='scene',phase_due=None,assessment_due=0,lat=j['lat'],lon=j['lon'])
        return j,v
    j,v=scene('77/002',65);engine.raise_radio(j,v,'Telenotarzt',reason_initial=True);tna_job=j['id']
    air,rtw=scene('77/011',30);air.update(lat=47.5,lon=15.8,crew_target='kh-hainburg');rtw.update(lat=air['lat'],lon=air['lon'])
    assert engine.maybe_request_transport_heli(air,rtw);air_job=air['id']
    engine.configure_events({'emergency_per_hour':0,'transport_per_hour':0,'transports_enabled':False})
    engine.save();sessions.close()
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);errors=[]
            def page(token):
                context=browser.new_context(viewport={'width':1440,'height':1000});context.route('https://tile.openstreetmap.org/**',lambda r:r.abort())
                context.add_init_script('sessionStorage.setItem("noe-token",'+json.dumps(token)+')')
                p=context.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.goto('http://127.0.0.1:8080');p.wait_for_function('state?.session');return p
            p=page(auth['token']);g=page(guest['token']);start_session(p)
            p.evaluate('id=>openDispatch(id)',tna_job);on_tab(p,'kommunikation')
            p.locator('#radio-detail [data-radio][data-step=listen]').click()
            on_tab(p,'nachforderung');p.locator('[data-tna-book]').click();p.wait_for_function('state.jobs.some(j=>j.telenotarzt)')
            expect(p.locator('[data-tna-phone]')).to_contain_text('SIM-000-000-01')
            g.wait_for_function('state.jobs.some(j=>j.telenotarzt)');g.evaluate('id=>openDispatch(id)',tna_job);on_tab(g,'gebucht')
            expect(g.locator('#detail-panel-gebucht .tna-resource')).to_contain_text('Telenotarzt');expect(g.locator('#detail-panel-gebucht .tna-resource .badge')).to_have_count(0)
            assert p.evaluate("state.telenotarzt_pool.available===9&&['SDS','ESApp'].every(c=>state.messages.some(m=>m.channel===c&&m.text.includes('SIM-000-000-01')))")
            assert not p.evaluate("[...mapObjects.keys()].some(k=>k.includes('tna-'))")
            p.evaluate("command('control',{paused:false,speed:15})")
            p.wait_for_function('state.jobs.some(j=>j.telenotarzt?.connected_at!=null)',timeout=10000);p.evaluate("command('control',{paused:true})")
            on_tab(p,'nachforderung');p.locator('[data-tna-release]').click();p.wait_for_function('state.telenotarzt_pool.available===10')
            g.wait_for_function('state.jobs.every(j=>!j.telenotarzt)')
            p.evaluate('id=>openDispatch(id)',air_job);on_tab(p,'kommunikation')
            p.locator('#radio-detail [data-radio][data-step=listen]').click()
            expect(p.locator('#radio-detail')).to_contain_text('Notarzthubschrauber')
            p.locator('#radio-detail [data-radio][data-step=unavailable]').click()
            p.wait_for_function("state.jobs.some(j=>j.request_denials?.NAH)")
            assert p.evaluate("state.logs.some(l=>l.text.includes('kein Notarzthubschrauber verfügbar'))")
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path='/tmp/noe-ui-qa/telemedicine.png');assert not errors,errors
            browser.close();print('Telenotarzt booking, status-free shared resource, SDS/ESApp phone, consultation, release and negative heli reply passed.')
    finally:proc.terminate();proc.wait(timeout=5)
