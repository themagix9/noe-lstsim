def on_tab(page, key):
    tab = page.locator('.detail-tabs [data-detail-tab="'+key+'"]')
    tab.wait_for(state='visible')
    if tab.get_attribute('aria-selected') != 'true':
        tab.click()
    return page

def choose_code(page, code):
    on_tab(page, 'disposition')
    from pathlib import Path
    Path('/tmp/noe-ui-qa').mkdir(exist_ok=True)
    assert page.evaluate('detailTab')=='disposition'
    page.screenshot(path='/tmp/noe-ui-qa/ampds-disposition.png')
    page.locator('#job-search').fill(code)
    page.locator('[data-code-choice="'+code+'"]').click()
    page.wait_for_function("code=>state.jobs.find(j=>j.id===selected)?.code===code&&state.jobs.find(j=>j.id===selected)?.code_confirmed",arg=code)

def start_session(page):
    from playwright.sync_api import expect
    from pathlib import Path
    previews=Path('/tmp/noe-ui-qa');previews.mkdir(exist_ok=True)
    expect(page.locator('#playback-overlay')).to_be_visible()
    expect(page.locator('#day-start')).to_have_text('Tag starten')
    if not (previews/'start-screen.png').exists():page.screenshot(path=str(previews/'start-screen.png'))
    page.locator('#day-start').click()
    expect(page.locator('#playback-overlay')).to_be_hidden()
    page.evaluate("command('control',{paused:true})")
    expect(page.locator('#playback-title')).to_have_text('Spiel pausiert')
    if not (previews/'pause-screen.png').exists():page.screenshot(path=str(previews/'pause-screen.png'))

def wait_for_auto_call(page, job=None):
    page.wait_for_function("id=>{const j=state.jobs.find(j=>j.id===(id||selected));return j?.call?.state==='ended'}",arg=job,timeout=45000)
    from playwright.sync_api import expect
    expect(page.locator('#call-next')).to_have_count(0)
    expect(page.locator('#call-continue')).to_be_enabled()
