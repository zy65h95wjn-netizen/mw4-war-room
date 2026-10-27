"""Optional local browser regression test (Playwright/Chromium required).
Uses injected fixture, because browser localhost navigation is disabled in this runner.
"""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text()
app=(ROOT/'app.js').read_text()
payload=(ROOT/'data/intel.json').read_text()
injection="""<script>
window._testFailure=false;
const testStorage = new Map();
Object.defineProperty(window, 'localStorage', {configurable:true, value:{
 getItem:k=>testStorage.has(k)?testStorage.get(k):null,
 setItem:(k,v)=>testStorage.set(k,String(v)),
 removeItem:k=>testStorage.delete(k)
}});
window.fetch=async()=>new Response(window._testFailure?'{"schema":999}':__PAYLOAD__, {status:200, headers:{'Content-Type':'application/json'}});
</script><script>__APP__</script>""".replace('__PAYLOAD__',json.dumps(payload)).replace('__APP__',app)
html=html.replace('<script src="app.js" defer></script>',injection)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 ctx=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
 page=ctx.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html,wait_until='domcontentloaded')
 page.get_by_text('Know the meta.').wait_for(timeout=10000)
 assert page.evaluate("localStorage.getItem('mw4-warroom-last-validated-intel-v021')") is not None
 assert 'REVIEWED OCT 27' in page.locator('#appMain').inner_text()
 # Re-fetch corrupted response on the same page, falling back to the prior valid copy.
 page.evaluate("window._testFailure=true;boot()")
 page.locator('text=Offline or previously saved briefing.').wait_for(timeout=10000)
 assert 'HAN 86' in page.locator('#appMain').inner_text()
 # Simulate time passing to test independent staleness and dated event status.
 page.evaluate("""() => {const RealDate=Date;window.Date=class extends RealDate { constructor(...a){super(...(a.length?a:['2026-11-10T12:00:00']))};static now(){return new RealDate('2026-11-10T12:00:00').getTime()} }; render(); }""")
 assert 'REVIEW OVERDUE' in page.locator('#appMain').inner_text()
 page.locator('#bottomNav button[data-page="season"]').click()
 assert 'LISTED WINDOW ENDED' in page.locator('#appMain').inner_text()
 assert 'STATUS UNVERIFIED' in page.locator('#appMain').inner_text()
 page.locator('#bottomNav button[data-page="meta"]').click()
 assert 'REVIEW OVERDUE' in page.locator('#appMain').inner_text()
 assert not errors, errors
 print('PASS: app loads valid fixture, saves last good, rejects corrupt JSON, uses offline copy, and flags stale sections/events (0 page errors)')
 ctx.close();b.close()