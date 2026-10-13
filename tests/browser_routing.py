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
    def log_message(self,*args):pass
    def do_GET(self):
        url=urlsplit(self.path)
        if url.path.startswith('/table/'):
            n=len(parse_qs(url.query)['sources'][0].split(';'))
            result={'code':'Ok','durations':[[120] for _ in range(n)],'distances':[[1500] for _ in range(n)]}
        else:
            a,b=[[float(x) for x in p.split(',')] for p in url.path.rsplit('/',1)[1].split(';')]
            result={'code':'Ok','routes':[{'duration':2400,'distance':2000,'geometry':{'coordinates':[a,[a[0],a[1]+.01],b]}}]}
        raw=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)

root=Path(__file__).resolve().parents[1]
routes=ThreadingHTTPServer(('127.0.0.1',0),OSRM);threading.Thread(target=routes.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'1','ROUTING_URL':f'http://127.0.0.1:{routes.server_port}','REINFORCEMENTS_AUTO':'0'},stdout=subprocess.DEVNULL)
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
            row=on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002');expect(row).to_contain_text('1.5 km Straße',timeout=15000);expect(row).to_contain_text('3 min');row.locator('input').check();p.locator('#dispatch').click();expect(p.locator('#dispatch-dialog')).not_to_be_visible();p.locator('#speed').select_option('60');p.locator('#pause').click()
            p.wait_for_function("state.vehicles.some(v=>v.callsign==='77/002'&&v.leg?.geometry)",timeout=20000);p.evaluate("command('control',{paused:true})")
            if p.locator('#dispatch-dialog').is_visible():p.locator('#close-dispatch').click()
            assert p.evaluate("mapLayers.getLayers().some(l=>l instanceof L.Polyline&&!(l instanceof L.CircleMarker)&&l.getLatLngs().length===3)")
            expect(p.locator('.station-marker.staffed').first).to_be_visible();expect(p.locator('.hospital-marker').first).to_be_visible()
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
            assert p.evaluate('document.documentElement.scrollHeight<=innerHeight+1')
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path='/tmp/noe-ui-qa/road-routing.png');assert not errors,errors
            print('Road routing browser test passed: address coordinates, street ETA, polyline, station and hospital icons.');browser.close()
    finally:proc.terminate();proc.wait(timeout=5);routes.shutdown();routes.server_close()
