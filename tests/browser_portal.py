"""Actual admin/player origins, registration, cross-device saves and chat boundary."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect
from browser_helpers import start_session

root=Path(__file__).resolve().parents[1];password='Dashboard-Browser-Password-2026!'
with tempfile.TemporaryDirectory() as data:
    proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=root,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'0','COOKIE_SECURE':'0','ADMIN_USERNAME':'dashboardadmin','ADMIN_PASSWORD':password,'RADIO_INTERVAL':'0','PATIENT_EVOLUTION':'0','REINFORCEMENTS_AUTO':'0'},stdout=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            for engine in (pw.chromium,pw.webkit):
                browser=engine.launch(headless=True);errors=[]
                def context():
                    ctx=browser.new_context(viewport={'width':1500,'height':1050});ctx.route('https://tile.openstreetmap.org/**',lambda route:route.abort());return ctx
                admin=context().new_page();admin.on('pageerror',lambda error:errors.append(str(error)));admin.goto('http://127.0.0.1:8081');admin.get_by_label('Administrator',exact=True).fill('dashboardadmin');admin.get_by_label('Passwort',exact=True).fill(password);admin.locator('#admin-login-form button').click();expect(admin.locator('#admin-shell')).to_be_visible()
                admin.locator('[data-page=defaults]').click();form=admin.locator('#defaults-form');form.locator('[name=emergency_per_hour]').fill('9');form.locator('[name=transports_enabled]').uncheck();form.locator('[name=hour]').fill('15');admin.wait_for_timeout(11000);expect(form.locator('[name=emergency_per_hour]')).to_have_value('9');form.get_by_role('button',name='Standards speichern',exact=True).click();expect(admin.locator('#admin-notice')).to_contain_text('Gespeichert')
                admin.locator('[data-page=maintenance]').click();maintenance=admin.locator('#maintenance-form');maintenance.locator('[name=maintenance_enabled]').check();maintenance.locator('[name=maintenance_message]').fill('Hier wird gerade live gearbeitet · '+engine.name);maintenance.locator('[name=registration_open]').check();maintenance.get_by_role('button').click();expect(admin.locator('#admin-notice')).to_contain_text('Gespeichert')
                player=context().new_page();player.on('pageerror',lambda error:errors.append(str(error)));player.goto('http://127.0.0.1:8080');expect(player.locator('#maintenance-banner')).to_contain_text('live gearbeitet');player.locator('#account-open').click();player.locator('#account-toggle').click();auth=player.locator('#account-auth');auth.locator('[name=username]').fill('player_'+engine.name);auth.locator('[name=display_name]').fill('Spieler '+engine.name);auth.locator('[name=password]').fill(password);auth.get_by_role('button').click();expect(player.locator('#account-content')).to_contain_text('Meine Sitzungen');player.locator('#close-account').click();player.locator('#mode-multi').click();player.locator('#lobby-submit').click();expect(player.locator('#lobby')).to_be_hidden();start_session(player)
                assert player.evaluate('state.session.registered&&state.session.chat_allowed&&state.event_settings.emergency_per_hour===9&&!state.event_settings.transports_enabled')
                assert player.evaluate("document.querySelector('header.desk-controls #leave-room')!==null && document.getElementById('leave-room').getBoundingClientRect().x<document.getElementById('clock').getBoundingClientRect().x")
                player.evaluate("command('generate',{kind:'transport'})");player.wait_for_function('state.jobs.length===1');job=player.evaluate('state.jobs[0].id');code=player.evaluate('state.session.code');player.locator('#leave-room').click();expect(player.locator('#lobby')).to_be_visible();player.locator('#account-open').click();expect(player.locator('[data-account-resume]')).to_have_count(1)
                # A fresh browser context has no room bearer or player cookie.
                restored=context().new_page();restored.on('pageerror',lambda error:errors.append(str(error)));restored.goto('http://127.0.0.1:8080');restored.locator('#account-open').click();login=restored.locator('#account-auth');login.locator('[name=username]').fill('player_'+engine.name);login.locator('[name=password]').fill(password);login.get_by_role('button').click();expect(restored.locator('[data-account-resume]')).to_have_count(1);restored.locator('[data-account-resume]').click();expect(restored.locator('#lobby')).to_be_hidden();assert restored.evaluate('id=>state.jobs.some(j=>j.id===id)',job)
                guest=context().new_page();guest.on('pageerror',lambda error:errors.append(str(error)));guest.goto('http://127.0.0.1:8080');guest.locator('#mode-multi').click();guest.locator('#lobby-join-tab').click();guest.get_by_label('Dein Disponentenname').fill('Gast '+engine.name);guest.get_by_label('Sitzungscode',exact=True).fill(code);guest.locator('#lobby-submit').click();expect(guest.locator('#lobby')).to_be_hidden();expect(guest.locator('#chat-form')).not_to_be_visible();assert guest.evaluate("fetch('/api/chat',{method:'POST',headers:authHeaders(),body:JSON.stringify({text:'Gast darf nicht senden'})}).then(r=>r.status)")==403
                restored.evaluate("command('chat',{text:'Registrierter Chat im Browser'})");restored.wait_for_function("state.chat.some(m=>m.text==='Registrierter Chat im Browser')");assert guest.evaluate('state.chat.length===0')
                admin.locator('[data-page=overview]').click();expect(admin.locator('#active-sessions')).to_contain_text('Gast '+engine.name,timeout=20000)
                Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);admin.screenshot(path='/tmp/noe-ui-qa/admin-'+engine.name+'.png',full_page=True)
                admin.set_viewport_size({'width':390,'height':844});admin.screenshot(path='/tmp/noe-ui-qa/admin-mobile-'+engine.name+'.png',full_page=True)
                admin.set_viewport_size({'width':1500,'height':1050})
                row=admin.locator('#active-sessions tr').filter(has_text=code)
                row.get_by_role('button',name='Löschen',exact=True).click()
                expect(admin.locator('#delete-room-dialog')).to_be_visible();expect(admin.locator('#delete-room-players')).to_contain_text('noch verbunden')
                admin.locator('#cancel-delete-room').click();expect(row).to_be_visible()
                row.get_by_role('button',name='Löschen',exact=True).click()
                admin.wait_for_timeout(11000);expect(admin.locator('#delete-room-dialog')).to_be_visible();expect(admin.locator('#delete-room-title')).to_contain_text(code)
                admin.locator('#confirm-delete-room').click();expect(admin.locator('#delete-room-dialog')).not_to_be_visible();expect(row).to_have_count(0)
                expect(restored.locator('#lobby')).to_be_visible(timeout=15000);expect(guest.locator('#lobby')).to_be_visible(timeout=15000)
                restored.locator('#account-open').click();expect(restored.locator('[data-account-resume]')).to_have_count(0)
                assert not errors,errors;browser.close();print(engine.name+': isolated admin, persistent accounts, cross-device resume, chat access, maintenance, preserved settings and top-left home passed.')
    finally:proc.terminate();proc.wait(timeout=5)
