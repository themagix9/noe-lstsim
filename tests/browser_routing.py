"""Routing UI integration against a local OSRM fixture, without external requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from playwright.sync_api import sync_playwright,expect
from browser_helpers import on_tab, choose_code, start_session

class OSRM(BaseHTTPRequestHandler):
    travel_seconds=2400
    def log_message(self,*args):pass
    def do_GET(self):
        url=urlsplit(self.path)
        if url.path.startswith('/table/'):
            n=len(parse_qs(url.query)['sources'][0].split(';'))
            result={'code':'Ok','durations':[[120] for _ in range(n)],'distances':[[1500] for _ in range(n)]}
        else:
            a,b=[[float(x) for x in p.split(',')] for p in url.path.rsplit('/',1)[1].split(';')]
            result={'code':'Ok','routes':[{'duration':self.travel_seconds,'distance':2000,'geometry':{'coordinates':[a,[a[0],a[1]+.01],b]}}]}
        raw=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)

root=Path(__file__).resolve().parents[1]
routes=ThreadingHTTPServer(('127.0.0.1',0),OSRM);threading.Thread(target=routes.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'RADIO_INTERVAL':'0','ROUTING_ENABLED':'1','ROUTING_URL':f'http://127.0.0.1:{routes.server_port}','REINFORCEMENTS_AUTO':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1366,'height':768})
            context.route('https://tile.openstreetmap.org/**',lambda r:r.fulfill(status=200,content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#edf1ee"/></svg>'))
            p=context.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto('http://127.0.0.1:8080');p.get_by_label('Dein Disponentenname').fill('Routingtest');p.locator('#lobby-submit').click();expect(p.locator('#lobby')).to_be_hidden();start_session(p)
            p.wait_for_function('addressPoints.length>500');address=p.evaluate("addressPoints.find(a=>a.city==='Schwechat').address")
            p.locator('#create-manual').click();p.locator('#manual-code').select_option('RD-1A1');p.get_by_label('Einsatzort / Adresse',exact=True).fill(address);p.get_by_label('Zusatztext',exact=True).click();p.locator('#manual-form button.primary').click()
            row=on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002');expect(row).to_contain_text('1.5 km Straße',timeout=15000);expect(row).to_contain_text('4 min');assert p.evaluate("(()=>{const j=state.jobs.find(j=>j.id===selected),v=state.vehicles.find(v=>v.callsign==='77/002'),eta=j.resource_eta[v.id];return eta.turnout_seconds>=85&&eta.turnout_seconds<=120&&eta.seconds===120*.85+eta.turnout_seconds})()");row.locator('input').check();p.locator('#dispatch').click();expect(p.locator('#dispatch-dialog')).not_to_be_visible();p.locator('#speed').select_option('60');p.locator('#pause').click()
            p.wait_for_function("state.vehicles.some(v=>v.callsign==='77/002'&&v.leg?.geometry)",timeout=20000);p.evaluate("command('control',{paused:true})")
            if p.locator('#dispatch-dialog').is_visible():p.locator('#close-dispatch').click()
            assert p.evaluate("![...mapObjects.keys()].some(k=>k.startsWith('route:'))"),'Routes must stay hidden by default'
            p.evaluate("mapObjects.get('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id).layer.fire('click')")
            assert p.evaluate("mapLayers.getLayers().some(l=>l instanceof L.Polyline&&!(l instanceof L.CircleMarker)&&l.getLatLngs().length===3)")
            p.evaluate("mapObjects.get('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id).layer.fire('click')")
            assert p.evaluate("![...mapObjects.keys()].some(k=>k.startsWith('route:'))")
            p.wait_for_function("mapObjects.get('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id)?.layer.getElement()?.querySelector('.map-status-number')?.textContent==='S2'")
            # Smooth map motion has many frames within a single server clock tick.
            p.evaluate("command('control',{paused:false,speed:1})")
            sampled=p.evaluate("""()=>new Promise(resolve=>{
             const id=state.vehicles.find(v=>v.callsign==='77/002').id,layer=mapObjects.get('vehicle:'+id).layer,groups=new Map(),until=performance.now()+600;
             function sample(){const point=layer.getLatLng(),key=state.clock;if(!groups.has(key))groups.set(key,new Set());groups.get(key).add(point.lat+','+point.lng);if(performance.now()<until)requestAnimationFrame(sample);else resolve(Math.max(...[...groups.values()].map(s=>s.size)))}sample()
            })""")
            assert sampled>=8,sampled
            p.evaluate("command('control',{paused:true})")
            still=p.evaluate("mapObjects.get('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id).layer.getLatLng()")
            p.wait_for_timeout(300)
            assert still==p.evaluate("mapObjects.get('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id).layer.getLatLng()")
            # Change only this unit's signalfahrt over an actual radio conversation.
            p.evaluate("openDispatch(state.vehicles.find(v=>v.callsign==='77/002').job)")
            on_tab(p,'gebucht').locator('[data-signal-resource]').first.click()
            p.locator('#radio-detail [data-signal-call][data-step=answer]').click()
            p.locator('#radio-detail [data-signal-call][data-step=confirm]').click()
            p.wait_for_function("state.vehicles.find(v=>v.callsign==='77/002').signal===false")
            assert p.evaluate("state.jobs.find(j=>j.id===selected).signal===true")
            assert not p.evaluate("mapObjects.get('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id).layer.getElement().classList.contains('blue-response')")
            p.locator('#close-dispatch').click()
            expect(p.locator('.station-marker.staffed').first).to_be_visible();expect(p.locator('.hospital-marker').first).to_be_visible()
            assert p.evaluate("state.hospitals.every(h=>mapObjects.has('hospital:'+h.id)===hospitalMapVisible(h))")
            assert p.evaluate("['kh-hainburg','kh-moedling','kh-donaustadt'].every(id=>mapObjects.has('hospital:'+id))")
            # Availability is local to the station, not merely a staffed shift.
            p.evaluate("()=>{window.stationTest=mapObjects.get('station:goetzendorf').layer;stationTest.openPopup()}")
            assert p.evaluate("stationTest.getElement().classList.contains('staffed')")
            p.evaluate("async()=>{for(const v of state.vehicles.filter(v=>v.station==='goetzendorf'&&!v.job))await command('vehicle_status',{vehicle:v.id,status:'6'})}")
            p.wait_for_function("stationTest.getElement().classList.contains('unstaffed')")
            assert p.evaluate("getComputedStyle(stationTest.getElement()).color==='rgb(196, 51, 63)'")
            assert p.evaluate("stationTest===mapObjects.get('station:goetzendorf').layer&&stationTest.isPopupOpen()")
            assert 'Keine verfügbaren Fahrzeuge auf Wache' in p.evaluate("stationTest.getPopup().getContent()")
            p.evaluate("()=>command('vehicle_status',{vehicle:state.vehicles.find(v=>v.callsign==='77/006').id,status:'1'})")
            p.wait_for_function("stationTest.getElement().classList.contains('staffed')")
            assert p.evaluate("stationTest.getElement().querySelector('span').textContent==='1'")
            p.evaluate("()=>command('vehicle_status',{vehicle:state.vehicles.find(v=>v.callsign==='77/006').id,status:'0'})")
            p.wait_for_function("stationTest.getElement().classList.contains('unstaffed')")
            assert not p.evaluate("stationTest.getElement().querySelector('span')!==null")
            # A neighbour helicopter enters the local fleet only after a reply.
            p.evaluate("()=>openDispatch(state.jobs.find(j=>j.vehicles.some(id=>state.vehicles.find(v=>v.id===id)?.callsign==='77/002')).id)")
            on_tab(p,'disposition')
            expect(p.locator('.resource-row').filter(has_text='Christophorus 15')).to_have_count(0)
            support_id=p.evaluate("state.vehicles.find(v=>v.callsign==='C15').id")
            on_tab(p,'support');p.locator('#support-vehicle').select_option(support_id)
            p.locator('#support-reason').fill('Keine lokalen Notarztmittel verfügbar')
            p.locator('#support-request').click()
            p.wait_for_function("state.jobs.some(j=>j.support_requests?.some(r=>r.state==='pending'))")
            p.evaluate("()=>command('control',{paused:false,speed:60})")
            p.wait_for_function("state.jobs.some(j=>j.support_requests?.some(r=>r.state==='accepted'))",timeout=15000)
            p.evaluate("()=>command('control',{paused:true})")
            assert p.evaluate("state.vehicles.find(v=>v.callsign==='C15').job===selected")
            assert p.evaluate("['SDS','ESApp'].every(channel=>state.messages.some(m=>m.vehicle===state.vehicles.find(v=>v.callsign==='C15').id&&m.channel===channel&&m.job===selected))")
            p.locator('#close-dispatch').click()
            # Scene resources collapse into coloured counts on the incident marker.
            p.evaluate("()=>{for(const call of ['77/002','77/099']){const v=state.vehicles.find(v=>v.callsign===call);v.job=selected;v.status='scene'}renderMap(state.vehicles.filter(relevant),state.jobs.filter(j=>j.status!=='done'))}")
            p.wait_for_function("!mapObjects.has('vehicle:'+state.vehicles.find(v=>v.callsign==='77/002').id)&&!mapObjects.has('vehicle:'+state.vehicles.find(v=>v.callsign==='77/099').id)")
            marker=p.locator('.incident-marker').filter(has=p.locator('.scene-count.unit-rtw'))
            expect(marker.locator('.scene-count.unit-rtw')).to_have_text('1');expect(marker.locator('.scene-count.unit-doctor')).to_have_text('1')
            assert p.evaluate("getComputedStyle(document.querySelector('.scene-count.unit-rtw')).color==='rgb(36, 99, 189)'&&getComputedStyle(document.querySelector('.scene-count.unit-doctor')).color==='rgb(180, 35, 45)'")
            assert p.evaluate('document.documentElement.scrollHeight<=innerHeight+1')
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path='/tmp/noe-ui-qa/road-routing.png');assert not errors,errors
            # Exercise the MANV entry point and live individual-patient UI.
            OSRM.travel_seconds=120
            p.evaluate("async()=>{await command('reset',{});await command('control',{paused:true});selected=null}")
            p.evaluate("document.getElementById('event-dialog').showModal()")
            p.locator('#manv-scenario').select_option('manv-bus');p.locator('#new-manv').click()
            p.wait_for_function("state.jobs.length===1")
            p.evaluate("""async()=>{
             const j=state.jobs.at(-1);window.manvId=j.id;
             await command('accept',{id:j.id});
             for(let i=0;i<3;i++){const call=state.jobs.find(j=>j.id===manvId).call,q=call.questions.find(q=>!call.answered.includes(q.key));await command('call_question',{job:manvId,question:q.key,combined:true})}
             await command('call_finish',{job:manvId});openDispatch(manvId)
            }""")
            expect(p.locator('#detail-tab-patienten')).to_have_count(0)
            choose_code(p,'RD-29B1')
            for call in ['77/002','77/099']:
                on_tab(p,'disposition').locator('.resource-row').filter(has_text=call).locator('input').check()
            p.locator('#dispatch').click();p.evaluate("command('control',{paused:false,speed:60})")
            p.wait_for_function("state.jobs.find(j=>j.id===manvId)?.patients?.length===6",timeout=75000)
            p.wait_for_function("state.vehicles.find(v=>v.callsign==='77/099')?.treating_patient!=null",timeout=20000)
            p.evaluate("async()=>{await command('control',{paused:true});openDispatch(manvId)}")
            on_tab(p,'patienten');expect(p.locator('.triage-patient')).to_have_count(6)
            expect(p.locator('.triage-I')).to_have_count(2)
            expect(p.locator('#detail-panel-patienten')).to_contain_text('Notarztversorgung: NEF')
            assert p.evaluate('document.documentElement.scrollHeight<=innerHeight+1')
            p.screenshot(path='/tmp/noe-ui-qa/manv-triage.png')
            # A negative reply ends the call and can be explicitly reset later.
            p.evaluate("command('radio_generate',{job:manvId,vehicle:state.vehicles.find(v=>v.callsign==='77/099').id,kind:'NEF',reason_initial:true})")
            on_tab(p,'kommunikation');p.locator('#radio-detail').get_by_role('button',name='LEO hört',exact=True).click()
            p.locator('#radio-detail [data-radio][data-step=unavailable]').click()
            p.wait_for_function("state.jobs.find(j=>j.id===manvId).request_denials?.NEF")
            assert p.evaluate("state.radio_calls.filter(c=>c.job===manvId&&c.kind==='NEF').every(c=>c.state==='closed')")
            on_tab(p,'nachforderung');expect(p.locator('[data-retry-request=NEF]')).to_be_visible();p.locator('[data-retry-request=NEF]').click()
            p.wait_for_function("!state.jobs.find(j=>j.id===manvId).request_denials?.NEF")
            assert not errors,errors
            print('Road routing and MANV browser test passed: street ETA, map icons, MANV call and live triage.');browser.close()
    finally:proc.terminate();proc.wait(timeout=5);routes.shutdown();routes.server_close()
