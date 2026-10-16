"""Real landing layout and CMP integration with all Google traffic intercepted."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://lstsim.stratosi.com'
MOCK=r"""
window.adTest={requests:[],revocations:0,initialPause:window.adsbygoogle.pauseAdRequests};
window.adsbygoogle.push=function(value){adTest.requests.push({pause:this.pauseAdRequests,slot:document.querySelector('#landing-ad-slot ins')?.dataset.adSlot});const el=document.querySelector('#landing-ad-slot ins');if(el){const box=document.createElement('div');box.textContent='Anzeigenvorschau · keine echte Werbung';box.style.cssText='padding:30px 12px;background:#e7edf4;color:#52677f;min-height:120px';el.append(box)}};
window.__tcfapi=function(command,version,callback){if(command==='addEventListener')window.testConsent=callback};
const callbacks=window.googlefc.callbackQueue;window.googlefc.showRevocationMessage=()=>adTest.revocations++;
window.googlefc.callbackQueue={push:value=>value.CONSENT_API_READY?.()};
for(const callback of callbacks)callback.CONSENT_API_READY?.();
"""

def main():
 with tempfile.TemporaryDirectory() as data:
  proc=subprocess.Popen([sys.executable,'app/server.py'],cwd=ROOT,env={**os.environ,'DATA_DIR':data,'ROUTING_ENABLED':'0','COOKIE_SECURE':'0'},stdout=subprocess.DEVNULL)
  try:
   for _ in range(80):
    try:urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=.5);break
    except OSError:time.sleep(.1)
   with sync_playwright() as pw:
    for engine in (pw.chromium,pw.webkit):
     browser=engine.launch(headless=True)
     for width in (1500,1100,390):
      enabled=False;external=[];errors=[]
      ctx=browser.new_context(viewport={'width':width,'height':1000})
      def intercept(route):
       url=urlsplit(route.request.url)
       if url.hostname=='lstsim.stratosi.com':
        response=route.fetch(url='http://127.0.0.1:8080'+url.path+('?' + url.query if url.query else ''))
        if url.path=='/api/site':
         config=response.json();config['advertising']['enabled']=enabled
         route.fulfill(response=response,json=config)
        else:route.fulfill(response=response)
       elif url.hostname=='pagead2.googlesyndication.com':
        external.append(route.request.url);route.fulfill(status=200,content_type='application/javascript',headers={'Access-Control-Allow-Origin':'*'},body=MOCK)
       else:route.abort()
      ctx.route('**/*',intercept);page=ctx.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.goto(ORIGIN)
      expect(page.locator('#account-open')).to_be_visible();expect(page.locator('#landing-ad')).to_be_hidden();assert not external
      enabled=True;page.reload()
      try:page.wait_for_function('window.adTest&&window.testConsent',timeout=10000)
      except Exception:
       print('Ad diagnostics:',engine.name,width,'external=',external,'errors=',errors,'page=',page.evaluate('({hidden:document.hidden,body:document.body.className,aside:document.getElementById("landing-ad").outerHTML,loader:document.getElementById("adsense-loader")?.outerHTML,ads:typeof LandingAds,google:typeof adTest,cmp:typeof __tcfapi})'),flush=True)
       raise
      expect(page.locator('#landing-ad')).to_be_visible();assert len(external)==1
      assert page.evaluate('adTest.initialPause===1&&adTest.requests.length===0&&adsbygoogle.pauseAdRequests===1')
      aside=page.locator('#landing-ad').bounding_box();form=page.locator('.lobby-card').bounding_box()
      if width>=1250:assert aside['x']>=form['x']+form['width']+24,(aside,form)
      else:assert aside['y']>=form['y']+form['height'],(aside,form)
      assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
      # Missing signal, rejected vendor, rejected storage, and failed CMP stay paused.
      for tc,success in [({},True),({'gdprApplies':True,'tcString':'mock','purpose':{'consents':{'1':True}},'vendor':{'consents':{'755':False}}},True),({'gdprApplies':True,'tcString':'mock','purpose':{'consents':{'1':False}},'vendor':{'consents':{'755':True}}},True),({'gdprApplies':False},False)]:
       page.evaluate('([data,ok])=>testConsent({cmpStatus:"loaded",eventStatus:"tcloaded",...data},ok)',[tc,success])
       assert page.evaluate('adsbygoogle.pauseAdRequests===1&&adTest.requests.length===0')
      valid={'cmpStatus':'loaded','eventStatus':'useractioncomplete','gdprApplies':True,'tcString':'mock-tcf-string','purpose':{'consents':{'1':True}},'vendor':{'consents':{'755':True}}}
      page.evaluate('data=>testConsent(data,true)',valid)
      assert page.evaluate('adTest.requests.length===1&&adTest.requests[0].pause===0&&adTest.requests[0].slot==="7480335427"')
      for _ in range(3):page.evaluate('data=>testConsent(data,true)',valid)
      assert page.evaluate('adTest.requests.length===1')
      Path('/tmp/noe-ui-qa').mkdir(exist_ok=True);page.screenshot(path=f'/tmp/noe-ui-qa/ads-{engine.name}-{width}.png',full_page=True)
      page.evaluate('()=>{document.getElementById("lobby").classList.add("hidden");document.body.classList.remove("lobby-open")}')
      expect(page.locator('#landing-ad')).not_to_be_visible();page.wait_for_function('adsbygoogle.pauseAdRequests===1')
      page.evaluate('()=>{document.getElementById("lobby").classList.remove("hidden");document.body.classList.add("lobby-open")}')
      page.wait_for_function('adsbygoogle.pauseAdRequests===0');assert page.evaluate('adTest.requests.length===1')
      page.locator('#ad-privacy').click();assert page.evaluate('adTest.revocations===1&&adsbygoogle.pauseAdRequests===1')
      valid['purpose']['consents']['1']=False;page.evaluate('data=>testConsent(data,true)',valid)
      expect(page.locator('#landing-ad-slot ins')).to_have_count(0);assert page.evaluate('adsbygoogle.pauseAdRequests===1')
      assert not errors,errors;ctx.close()
     browser.close();print(engine.name+': disabled by default, desktop/tablet/mobile layout, Google CMP gate, single request, game pause and revocation passed')
  finally:proc.terminate();proc.wait(timeout=5)

if __name__=='__main__':main()
