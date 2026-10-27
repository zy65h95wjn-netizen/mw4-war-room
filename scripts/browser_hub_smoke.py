"""Local real-Chromium smoke tests. Requires only local Playwright installation."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / 'index.html').read_text(encoding='utf-8')
logic = (ROOT / 'logic.js').read_text(encoding='utf-8')
app = (ROOT / 'app.js').read_text(encoding='utf-8')
feed = (ROOT / 'data/intel.json').read_text(encoding='utf-8')
injection = '<script>window.fetch=async()=>new Response(' + json.dumps(feed) + ',{status:200,headers:{"Content-Type":"application/json"}})</script>'
injection += '<script>' + logic + '</script><script>' + app + '</script>'
html = html.replace('<script src="logic.js" defer></script>\n<script src="app.js" defer></script>', injection)
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        for width in [320,390,430]:
            context=browser.new_context(viewport={'width':width,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True,timezone_id='America/New_York',service_workers='block')
            page=context.new_page()
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content(html,wait_until='domcontentloaded')
            page.get_by_text('Know the meta.',exact=False).wait_for(timeout=15000)
            labels=[x.inner_text() for x in page.locator('#bottomNav button').all()]
            assert labels==['⌂\nBrief','⌖\nWeapons','≡\nUpdates','◉\nEvents','▤\nPass'],labels
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),f'overflow brief @ {width}'
            page.locator('#bottomNav').get_by_role('button',name='Weapons').click()
            assert 'Rankings & available builds' in page.locator('#appMain').inner_text()
            assert 'HAN 86' in page.locator('#appMain').inner_text()
            assert page.locator('#ironSwitch').is_checked()
            assert 'FTAC' not in page.locator('#appMain').inner_text() or 'HAN 86' in page.locator('#appMain').inner_text()
            page.locator('#appMain').get_by_role('button',name='WZStats',exact=False).click()
            assert 'Axion' in page.locator('#appMain').inner_text()
            page.locator('#appMain').get_by_role('button',name='SMG',exact=True).click()
            assert 'HAN 86' not in page.locator('.taprow').all_inner_texts(), 'rank category filter broken'
            page.locator('#appMain').get_by_role('button',name='All',exact=True).click()
            page.locator('.taprow').filter(has_text='Axion').first.click()
            main=page.locator('#appMain').inner_text()
            assert 'GS50 Grip' in main, 'Axion attached build missing'
            assert 'CODMunity' in main and 'WZStats' in main, 'separate source rankings missing'
            page.locator('#appMain').get_by_role('button',name='Copy build',exact=True).count()==1
            page.locator('#appMain').get_by_role('button',name='HAN 86').first.click()
            assert 'IRON SIGHTS' in page.locator('#appMain').inner_text().upper()
            page.locator('#ironSwitch').uncheck()
            assert 'Versatile · source meta' in page.locator('#appMain').inner_text()
            page.locator('#appMain').get_by_role('button',name='Versatile · source meta').click()
            assert 'ZLR Type C' in page.locator('#appMain').inner_text()
            page.locator('#bottomNav').get_by_role('button',name='Updates').click()
            assert 'Launch fixes: XP and class editing' in page.locator('#appMain').inner_text()
            assert 'All official patch notes' in page.locator('#appMain').inner_text()
            page.locator('#bottomNav').get_by_role('button',name='Events').click()
            main=page.locator('#appMain').inner_text()
            assert all(word in main for word in ['Boot Camp','Shipment','Possession','Infected']),main[:500]
            assert 'availability unverified' in main.lower(),main[:1200]
            assert 'reported window' in main.lower(),main[:1200]
            page.locator('#bottomNav').get_by_role('button',name='Pass').click()
            assert 'BlackCell' in page.locator('#appMain').inner_text()
            page.locator('#sourcesBtn').click()
            assert page.locator('#overlay').is_visible()
            page.locator('#closeSheet').click()
            assert page.locator('#overlay').is_hidden()
            for button in ['Brief','Weapons','Updates','Events','Pass']:
                page.locator('#bottomNav').get_by_role('button',name=button).click()
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),f'overflow {button} @ {width}'
            assert not errors,errors
            print(f'PASS {width}px: 5 navigation targets; unified ranks/builds; category/search; events; pass; modal; no overflow or script errors')
            context.close()
        browser.close()
finally:
    pass