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
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'RADIO_INTERVAL':'0','ROUTING_ENABLED':'0','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1100})
            context.route('https://tile.openstreetmap.org/**',lambda r:r.abort());p=context.new_page();errors=[];requests=[]
            p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:requests.append(r.url));p.goto('http://127.0.0.1:8080');p.get_by_label('Dein Disponentenname').fill('Livetest');p.locator('#lobby-submit').click();expect(p.locator('#lobby')).to_be_hidden();start_session(p)
            assert p.evaluate('leafletMap.getZoom()===13&&leafletMap.getMaxZoom()===18')
            p.evaluate('leafletMap.setZoom(11)');expect(p.locator('#map')).to_have_class(__import__('re').compile('map-icons-small'));p.evaluate('leafletMap.setZoom(13)')
            p.locator('#pause').click();p.locator('#create-manual').click();expect(p.locator('#manual-code')).to_have_value('')
            p.get_by_label('Einsatzort / Adresse',exact=True).fill('Schwechat Testadresse');p.locator('#manual-form button.primary').click();expect(p.locator('#manual-dialog')).to_be_visible();assert p.evaluate('state.jobs.length')==0
            expect(p.locator('#manual-signal')).to_be_checked();p.locator('#manual-signal').uncheck();p.locator('#manual-code').select_option('RD-1A1');expect(p.locator('#manual-signal')).not_to_be_checked();p.locator('#manual-form button.primary').click();expect(p.locator('#dispatch-dialog')).to_be_visible()
            on_tab(p, 'einsatz').locator('#job-additional').focus();p.evaluate("window.stableText=document.getElementById('job-additional')")
            on_tab(p, 'einsatz').locator('#job-additional').press_sequentially('Text bleibt erhalten',delay=200)
            assert p.evaluate("stableText===document.getElementById('job-additional')&&document.activeElement===stableText")
            expect(on_tab(p, 'einsatz').locator('#job-additional')).to_have_value('Text bleibt erhalten')
            assert p.locator('.detail-tabs [role="tab"]').all_text_contents()[:3]==['Kommunikation','Disposition','Einsatzdaten']
            on_tab(p,'disposition');expect(p.locator('#job-search')).to_be_visible();expect(p.locator('#job-signal')).not_to_be_checked();p.locator('#job-signal').check();p.wait_for_function('state.jobs.find(j=>j.id===selected).signal===true');p.locator('#job-signal').uncheck();p.wait_for_function('state.jobs.find(j=>j.id===selected).signal===false')
            expect(p.locator('#detail-tab-nachforderung')).to_be_visible();expect(p.locator('#detail-tab-support')).to_be_visible()
            on_tab(p, 'disposition').locator('[data-filter="RTW"]').click();assert p.evaluate("[...document.querySelectorAll('.resource-row')].every(e=>['RTW','RTW-C'].includes(state.vehicles.find(v=>v.id===e.dataset.resourceId).type))")
            row=on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002');expect(row).to_contain_text('RTW 77/002');row.locator('input').check();on_tab(p, 'einsatz');expect(p.locator('#detail-panel-disposition')).to_be_hidden();expect(p.locator('#job-additional')).to_have_value('Text bleibt erhalten');on_tab(p, 'disposition');expect(row.locator('input')).to_be_checked()
            # Compact laptop window: only the resource list scrolls, checked rows green.
            p.set_viewport_size({'width':1366,'height':768});p.wait_for_timeout(250)
            expect(row).to_have_attribute('aria-checked','true')
            assert p.evaluate("getComputedStyle(document.querySelector('.resource-row[aria-checked=true]')).backgroundColor==='rgb(216, 241, 223)'")
            assert p.evaluate("(()=>{const d=document.getElementById('dispatch-dialog'),a=document.getElementById('detail'),b=document.getElementById('detail-panel-disposition');return d.scrollHeight<=d.clientHeight+1&&a.scrollHeight<=a.clientHeight+1&&b.scrollHeight<=b.clientHeight+1})()")
            p.evaluate("document.querySelector('.resource-list').scrollTop=500")
            on_tab(p,'einsatz');on_tab(p,'disposition');assert p.evaluate("document.querySelector('.resource-list').scrollTop") == 0
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path='/tmp/noe-ui-qa/compact-disposition.png')
            p.set_viewport_size({'width':1440,'height':1100})
            on_tab(p, 'disposition').locator('[data-filter="NA"]').click();expect(on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002')).to_have_count(0)
            on_tab(p, 'disposition').locator('[data-filter="RTW"]').click();expect(on_tab(p, 'disposition').locator('.resource-row').filter(has_text='77/002').locator('input')).to_be_checked()
            on_tab(p, 'disposition').locator('#resource-sort').select_option('callsign');on_tab(p, 'disposition').locator('#resource-direction').select_option('desc')
            assert p.evaluate("(()=>{const rows=[...document.querySelectorAll('.resource-row')].map(e=>state.vehicles.find(v=>v.id===e.dataset.resourceId));return rows.every((v,i)=>!i||rows[i-1].callsign.localeCompare(v.callsign,'de',{numeric:true})>=0)})()")
            expect(on_tab(p, 'einsatz').locator('#job-additional')).to_have_value('Text bleibt erhalten');p.locator('#close-dispatch').click()
            p.evaluate("()=>openDispatch(selected)");on_tab(p,'disposition')
            expect(p.locator('#resource-sort')).to_have_value('distance');expect(p.locator('#resource-direction')).to_have_value('asc')
            assert p.evaluate("document.querySelector('.resource-list').scrollTop") == 0
            p.locator('#close-dispatch').click()
            assert p.evaluate("(()=>{const card=document.querySelector('.job'),button=card.querySelector('.job-expand').getBoundingClientRect(),text=card.querySelector('.job-open').getBoundingClientRect();return button.right<=text.left&&button.height>=48})()"),'Expand control overlaps incident text'
            assert p.evaluate("(()=>{const all=state.vehicles.filter(relevant),grouped=poolResources(all),idle=grouped.filter(v=>v.type==='FR'&&!v.job);return idle.length>2&&new Set(idle.map(v=>v.fr_pool)).size===idle.length&&idle.length<all.filter(v=>v.type==='FR').length})()")
            # UI clock interpolates without fetching /api/state every two seconds.
            start=p.locator('#clock').inner_text();p.wait_for_timeout(1200);assert p.locator('#clock').inner_text()!=start
            p.locator('#pause').click();expect(p.locator('#running')).to_have_text('SIMULATION PAUSIERT');start=p.locator('#clock').inner_text();p.wait_for_timeout(1300);expect(p.locator('#clock')).to_have_text(start)
            p.locator('#create-manual').click();p.locator('#manual-kind').select_option('transport');expect(p.locator('#manual-code')).to_have_value('');p.locator('#manual-search').fill('Dialyse');expect(p.locator('#manual-code option[value="KTR-93Y2"]')).to_have_count(1);p.locator('#manual-code').select_option('KTR-93Y2');p.get_by_label('Einsatzort / Adresse',exact=True).fill('Transportadresse Schwechat');p.locator('#manual-form button.primary').click()
            expect(p.locator('#reserve-vehicle option').filter(has_text='77/050')).to_contain_text('RK Himberg');expect(p.locator('#reserve-vehicle option').filter(has_text='77/050')).to_contain_text('km Luftlinie');expect(p.locator('#detail')).to_contain_text('Abholzeit');assert on_tab(p, 'einsatz').locator('#job-pickup').get_attribute('step')=='1800';expect(p.locator('.job.transport .pickup-time.urgent')).to_be_visible();on_tab(p, 'disposition').locator('[data-filter="KTW"]').click();assert p.evaluate("[...document.querySelectorAll('.resource-row')].every(e=>['KTW','KTW-B','BKTW'].includes(state.vehicles.find(v=>v.id===e.dataset.resourceId).type))")
            on_tab(p, 'disposition').locator('#resource-sort').select_option('status');on_tab(p, 'disposition').locator('#resource-direction').select_option('asc');p.wait_for_timeout(1500);expect(on_tab(p, 'disposition').locator('#resource-sort')).to_have_value('status');expect(p.locator('#manual-dialog')).not_to_be_visible()
            # Vordisposition permits only S1/S5/S6; live status changes revoke selection.
            reserve_id=p.evaluate("state.vehicles.find(v=>v.callsign==='77/005').id")
            assert p.evaluate("(()=>{const v=state.vehicles.find(v=>v.callsign==='77/005'),j=state.jobs.find(j=>j.id===selected);return ['ready','hospital','radio'].every(status=>canReserve({...v,status},j))&&['enroute','scene','transport','duty','standby','acknowledged','out','assigned'].every(status=>!canReserve({...v,status},j))})()")
            p.evaluate("id=>command('vehicle_status',{vehicle:id,status:'6'})",reserve_id)
            p.locator('#reserve-vehicle').select_option(reserve_id);expect(p.locator('#reserve')).to_be_enabled()
            for status in ['7','0','8']:
                p.evaluate("({id,status})=>command('vehicle_status',{vehicle:id,status})",{'id':reserve_id,'status':status})
                expect(p.locator('#reserve-vehicle option[value="'+reserve_id+'"]').first).to_be_disabled()
                expect(p.locator('#reserve')).to_be_disabled()
            p.evaluate("id=>command('vehicle_status',{vehicle:id,status:'1'})",reserve_id)
            expect(p.locator('#reserve-vehicle option[value="'+reserve_id+'"]').first).to_be_enabled()
            p.locator('#reserve-vehicle').select_option(reserve_id);expect(p.locator('#reserve')).to_be_enabled()
            p.locator('#reserve-vehicle').select_option('');expect(p.locator('#reserve')).to_be_disabled()
            # Actual browser audio graph: three bell partials, once despite live updates.
            p.evaluate("()=>{window.gongTones=0;const original=AudioContext.prototype.createOscillator;AudioContext.prototype.createOscillator=function(){window.gongTones++;return original.call(this)}}")
            p.locator('#close-dispatch').click();p.locator('#pause').click();p.wait_for_function('window.gongTones===3');p.wait_for_timeout(1200);assert p.evaluate('window.gongTones')==3
            p.locator('#pause').click()
            # Reserved ready transport can be alarmed directly from the list.
            p.evaluate("()=>{const j=state.jobs.find(j=>j.kind==='transport');window.quickId=j.id;return command('reserve',{job:j.id,vehicle:state.vehicles.find(v=>v.callsign==='77/003').id})}")
            quick=p.locator('[data-quick-alarm]');expect(quick).to_be_visible();expect(p.locator('.job.pickup-ready')).to_be_visible()
            quick.click();expect(p.locator('#dispatch-dialog')).not_to_be_visible();p.wait_for_function("state.vehicles.find(v=>v.callsign==='77/003').job===window.quickId")
            # Crew fuel approval and dispatcher-initiated per-unit cancellation in the UI.
            p.evaluate("()=>command('vehicle_status',{vehicle:state.vehicles.find(v=>v.callsign==='77/004').id,status:'6'})")
            p.evaluate("()=>command('fuel_request',{vehicle:state.vehicles.find(v=>v.callsign==='77/004').id})")
            p.locator('#radio-queue [data-fuel][data-step="listen"]').click();p.locator('#radio-queue [data-fuel][data-step="deny"]').click()
            p.wait_for_function("state.radio_calls.filter(c=>c.kind==='Tanken').every(c=>c.state==='closed')");assert p.evaluate("state.vehicles.find(v=>v.callsign==='77/004').status==='radio'")
            p.evaluate("()=>command('fuel_request',{vehicle:state.vehicles.find(v=>v.callsign==='77/004').id})")
            p.locator('#radio-queue [data-fuel][data-step="listen"]').click();p.locator('#radio-queue [data-fuel][data-step="allow"]').click()
            p.wait_for_function("state.vehicles.find(v=>v.callsign==='77/004').status==='duty'")
            p.evaluate("()=>command('dispatch',{job:state.jobs.find(j=>j.kind==='emergency').id,vehicles:[state.vehicles.find(v=>v.callsign==='77/002').id]})")
            p.evaluate("()=>openDispatch(state.jobs.find(j=>j.kind==='emergency').id)")
            on_tab(p,'gebucht').locator('[data-call-resource]').click()
            on_tab(p,'kommunikation').locator('#radio-detail [data-cancel][data-step="answer"]').click()
            on_tab(p,'kommunikation').locator('#radio-detail [data-cancel][data-step="cancel"]').click()
            p.wait_for_function("state.vehicles.find(v=>v.callsign==='77/002').job===null")
            assert p.evaluate("new Set(state.messages.filter(m=>m.text.startsWith('EINSATZSTORNO')).map(m=>m.channel)).size===2")
            if p.locator('#dispatch-dialog').is_visible():p.locator('#close-dispatch').click()
            p.locator('#desk-menu summary').click();p.locator('[data-view="settings"]').click()
            p.locator('#icon-resource-search').fill('77/004');expect(p.locator('#icon-resource option')).to_have_count(1)
            p.locator('#icon-graphic').select_option('box');expect(p.locator('#resource-icon-preview')).to_have_attribute('src','/graphics/box.svg')
            p.wait_for_timeout(1500);expect(p.locator('#icon-graphic')).to_have_value('box')
            p.locator('#save-resource-icon').click();p.wait_for_function("state.vehicles.find(v=>v.callsign==='77/004').graphic==='box'")
            assert p.evaluate("state.vehicles.find(v=>v.callsign==='77/004').status==='duty'")
            # Oversized source images are optimized before upload, keeping alpha.
            optimized=p.evaluate("""async()=>{
             const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=1000;
             const ctx=canvas.getContext('2d'),pixels=ctx.createImageData(1600,1000);
             for(let offset=0;offset<pixels.data.length;offset+=65536)crypto.getRandomValues(pixels.data.subarray(offset,Math.min(offset+65536,pixels.data.length)));
             for(let y=0;y<1000;y++)for(let x=0;x<20;x++)pixels.data[(y*1600+x)*4+3]=0;
             ctx.putImageData(pixels,0,0);const source=await new Promise(r=>canvas.toBlob(r,'image/png'));
             const result=await GraphicUpload.optimize(source),image=await createImageBitmap(result);
             canvas.width=image.width;canvas.height=image.height;ctx.drawImage(image,0,0);
             const value={original:source.size,size:result.size,width:image.width,height:image.height,alpha:ctx.getImageData(0,0,1,1).data[3]};image.close();return value
            }""")
            assert optimized['original']>512*1024 and optimized['size']<=512*1024,optimized
            assert optimized['width']<=512 and optimized['height']<=256 and optimized['alpha']==0,optimized
            # Job summaries are collapsed by default and only one can be expanded.
            p.evaluate("async()=>{await command('generate',{kind:'transport'});await command('generate',{kind:'transport'});document.querySelector('[data-view=desk]').click()}")
            expect(p.locator('[data-expand-job][aria-expanded=true]')).to_have_count(0)
            p.locator('[data-expand-job]').nth(0).click();expect(p.locator('.job-expanded:visible')).to_have_count(1)
            p.locator('[data-expand-job]').nth(1).click();expect(p.locator('.job-expanded:visible')).to_have_count(1)
            expanded=p.locator('[data-expand-job][aria-expanded=true]').get_attribute('data-expand-job');p.wait_for_timeout(1200)
            expect(p.locator('[data-expand-job][aria-expanded=true]')).to_have_attribute('data-expand-job',expanded)
            expect(p.locator('#dispatch-dialog')).not_to_be_visible()
            p.locator('.job-open').first.click();expect(p.locator('#dispatch-dialog')).to_be_visible();p.locator('#close-dispatch').click()
            assert not any(u.endswith('/api/state') for u in requests),requests;assert not errors,errors
            Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);p.screenshot(path='/tmp/noe-ui-qa/live-filter-sort.png');browser.close();print('Live editing, empty code, clock, filter, sort and preserved selection browser tests passed.')
    finally:proc.terminate();proc.wait(timeout=5)
