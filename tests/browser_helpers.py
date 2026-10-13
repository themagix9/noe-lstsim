def on_tab(page, key):
    tab = page.locator('.detail-tabs [data-detail-tab="'+key+'"]')
    tab.wait_for(state='visible')
    if tab.get_attribute('aria-selected') != 'true':
        tab.click()
    return page

def choose_code(page, code):
    on_tab(page, 'einsatz')
    page.locator('#job-search').fill(code)
    page.locator('[data-code-choice="'+code+'"]').click()

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
