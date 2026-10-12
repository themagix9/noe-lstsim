"""Exercise real clicks/taps on rows, not just programmatic AAO selection."""
import os
import json
import threading
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from playwright.sync_api import sync_playwright,expect

root=Path(__file__).resolve().parents[1]
class Routing(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        query=parse_qs(urlsplit(self.path).query);n=len(query.get('sources',['0'])[0].split(';'))
        body=json.dumps({'code':'Ok','durations':[[120] for _ in range(n)],'distances':[[1500] for _ in range(n)]}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
router=ThreadingHTTPServer(('127.0.0.1',0),Routing);threading.Thread(target=router.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'1','ROUTING_URL':f'http://127.0.0.1:{router.server_port}','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            for browser_type in (pw.chromium,pw.webkit):
                browser=browser_type.launch(headless=True);context=browser.new_context(viewport={'width':1366,'height':1024},has_touch=True,is_mobile=True)
                context.route('https://tile.openstreetmap.org/**',lambda r:r.abort());p=context.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
                p.goto('http://127.0.0.1:8080');p.get_by_label('Dein Disponentenname').fill('Touchdisponent');p.locator('#lobby-submit').click();expect(p.locator('#lobby')).to_be_hidden()
                p.evaluate("command('generate',{kind:'emergency'})");expect(p.locator('#accept')).to_be_visible();job=p.evaluate('state.jobs.at(-1).id')
                p.wait_for_function("leafletMap.getZoom()===13 && leafletMap.getCenter().distanceTo([state.jobs.at(-1).lat,state.jobs.at(-1).lon])<150")
                assert not p.evaluate("document.getElementById('dispatch-dialog').matches(':modal')")
                expect(p.locator('#pause')).to_be_enabled();p.locator('#pause').click();expect(p.locator('#running')).to_have_text('SIMULATION LÄUFT')
                p.locator('#accept').tap();expect(p.locator('.call-dialogue')).to_contain_text('Rettungsleitstelle Niederösterreich, wo genau ist der Notfallort?');expect(p.locator('#dispatch')).to_be_disabled()
                for _ in range(6):
                    with p.expect_response(lambda r:r.url.endswith('/api/call_question')) as answer:p.locator('#call-next').tap()
                    assert answer.value.ok,answer.value.text()
                expect(p.locator('#call-finish')).to_be_visible();p.locator('#call-finish').tap();expect(p.locator('.call-dialogue')).to_contain_text('Telefonat beendet');expect(p.locator('.call-dialogue')).to_contain_text('Wir schicken jemanden zu Ihnen.')
                p.locator('#job-search').fill('RD-17B1');p.locator('#job-code').select_option('RD-17B1');p.locator('[data-filter="RTW"]').tap()
                row=p.locator('.resource-row').filter(has_text='77/002');expect(row).to_contain_text('km Straße',timeout=15000);row.locator('b').tap();expect(row.locator('input')).to_be_checked();p.wait_for_timeout(1500);expect(row.locator('input')).to_be_checked()
                row.locator('b').tap();expect(row.locator('input')).not_to_be_checked();row.locator('input').tap();expect(row.locator('input')).to_be_checked();p.wait_for_timeout(1200);expect(row.locator('input')).to_be_checked()
                # Preserve state while sorting and continue to interact with the map.
                p.locator('#resource-sort').select_option('status');expect(row.locator('input')).to_be_checked()
                p.evaluate("window.stableMarker=mapObjects.get('station:schwechat').layer;stableMarker.openPopup();leafletMap.setView([48.14,16.49],12,{animate:false});window.stableCenter=leafletMap.getCenter()")
                p.wait_for_timeout(2500)
                stable=p.evaluate("({same:stableMarker===mapObjects.get('station:schwechat').layer,open:stableMarker.isPopupOpen(),zoom:leafletMap.getZoom(),center:leafletMap.getCenter(),before:stableCenter})")
                assert stable['same'] and stable['open'] and stable['zoom']==12 and abs(stable['center']['lat']-stable['before']['lat'])<.00001,stable
                p.locator('#detail').evaluate('e=>e.scrollTop=0')
                title=p.locator('#dispatch-dialog > .panel-head');before=p.locator('#dispatch-dialog').bounding_box();box=title.bounding_box()
                p.mouse.move(box['x']+100,box['y']+18);p.mouse.down();p.mouse.move(box['x']-100,box['y']+60,steps=6);p.mouse.up();after=p.locator('#dispatch-dialog').bounding_box();assert abs(after['x']-before['x'])>100,(before,after)
                Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path=f'/tmp/noe-ui-qa/caller-window-{browser_type.name}.png')
                p.locator('#dispatch').click();expect(p.locator('#dispatch-dialog')).not_to_be_visible();p.wait_for_function("state.jobs.find(j=>j.id==="+repr(job)+").vehicles.length===1")
                assert p.evaluate("state.vehicles.find(v=>v.callsign==='77/002').status==='assigned'");assert not errors,errors
                browser.close();print(browser_type.name+': manual row and checkbox taps, live state, map, draggable window and caller dialogue passed.')
    finally:proc.terminate();proc.wait(timeout=5);router.shutdown();router.server_close()
