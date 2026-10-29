'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { weaponCatalog, eventTiming, orderedEvents } = require('../logic.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/intel.json'), 'utf8'));

test('each weapon has one canonical record and merged source-specific rankings', () => {
  const weapons = weaponCatalog(data);
  assert.equal(new Set(weapons.map(x => x.weapon)).size, weapons.length);
  const han = weapons.find(w => w.weapon === 'HAN 86');
  assert.equal(han.category, 'AR');
  assert.ok(han.builds.some(b => b.id === 'han-iron'));
  assert.ok(han.rankings.length > 0);
  assert.ok(weapons.find(w => w.weapon === data.meta[0].entries[0].weapon).rankings.some(r => r.board === 'cod'));
  assert.ok(han.rankings.some(r => r.board === 'wz'));
  assert.equal(weapons.find(w => w.weapon === 'Axion').builds.some(b => !b.optic), true);
});

test('the weapon catalog rejects category mismatches', () => {
  const bad = structuredClone(data);
  bad.builds[0].category = 'SMG';
  assert.throws(() => weaponCatalog(bad), /Conflicting weapon category/);
});

test('event windows distinguish announced, reported, unknown, and ended without falsely claiming live', () => {
  const date = new Date(2026, 9, 27, 14, 0);
  const future = { starts: '2026-10-29', ends: null, scheduleConfidence: 'official' };
  const reported = { starts: '2026-10-28', ends: '2026-11-04', scheduleConfidence: 'reported' };
  const window = { starts: '2026-10-20', ends: '2026-10-30', scheduleConfidence: 'official' };
  const unknown = { starts: '2026-10-23', ends: null, scheduleConfidence: 'official' };
  const ended = { starts: '2026-10-01', ends: '2026-10-26', scheduleConfidence: 'reported' };
  assert.deepEqual([future, reported, window, unknown, ended].map(e => eventTiming(e, date).kind), ['upcoming','upcoming','window','unconfirmed','ended']);
  assert.match(eventTiming(reported, date).label, /reported/i);
  assert.match(eventTiming(window, date).label, /announced window/i);
  assert.match(eventTiming(unknown, date).label, /unverified/i);
  assert.ok(orderedEvents([ended, unknown, future, window], date).map(e => e).indexOf(ended) === 3);
});

test('same-day event end is within listed window, not ended', () => {
  const event = { starts: '2026-10-23', ends: '2026-10-27', scheduleConfidence: 'reported' };
  assert.equal(eventTiming(event, new Date(2026, 9, 27)).kind, 'window');
  assert.equal(eventTiming(event, new Date(2026, 9, 28)).kind, 'ended');
});

const vm = require('node:vm');

// Exercise the real app click handler without network or a heavyweight browser dependency.
function loadoutHarness() {
  const handlers = new Map();
  let reveals = 0;
  const elements = {
    appMain: { innerHTML: '', dataset: {} },
    loadoutDialog: {open:false,addEventListener(){},showModal(){this.open=true},close(){this.open=false}},
    loadoutContent: {innerHTML:'',querySelector(){return {focus(){}}}},
    closeLoadout: {focus(){}},
    bottomNav: { innerHTML: '' },
    overlay: { hidden: true, addEventListener() {} },
    toast: { textContent: '', classList: { add() {}, remove() {} } }
  };
  const document = {
    body:{classList:{add(){},remove(){}}},
    getElementById(id) {
      if (id === 'weaponLoadout') {
        return elements.appMain.innerHTML.includes('id="weaponLoadout"')
          ? { scrollIntoView() { reveals++; } } : null;
      }
      return elements[id] || null;
    },
    addEventListener(type, fn) { handlers.set(type, fn); }
  };
  const app = fs.readFileSync(path.join(__dirname, '../app.js'), 'utf8').replace(/\r\n/g, '\n');
  const bootIndex = app.lastIndexOf('\nboot();\n');
  assert.ok(bootIndex > 0, 'boot invocation marker must exist');
  const context = vm.createContext({
    console, document, window: { scrollTo() {} },
    navigator: { onLine: true }, localStorage: { getItem() { return null; }, setItem() {} },
    WarRoomLogic: require('../logic.js'), WarRoomStore: require('../store.js'), WarRoomArsenal: require('../arsenal.js'), URL, setTimeout, clearTimeout
  });
  vm.runInContext(app.slice(0, bootIndex), context, { filename: 'app.js' });
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../armory-ui.js'),'utf8'), context, {filename:'armory-ui.js'});
  context.testIntel = data;
  vm.runInContext('state.feed=testIntel; bindEvents(); render();', context);
  function click(dataset) {
    const button = { id: '', dataset };
    handlers.get('click')({ target: { closest(selector) { assert.equal(selector, 'button'); return button; } } });
  }
  return { elements, context, click, reveals: () => reveals, handlers, html:()=>elements.appMain.innerHTML+(elements.loadoutDialog.open?elements.loadoutContent.innerHTML:'') };
}

test('overview keeps source-specific leaders, actual patch and season dates, artwork and attribution',()=>{
 const h=loadoutHarness(),html=h.html();
 for(const term of ['Axion','VEL 46','ISO Nightshade','CODMunity · Overall','WZStats · SMG',data.patches[0].title,data.battlePass.label,'Data from itemshop.gg','Reviewed Oct 28','illustrative art']) assert.ok(html.includes(term),term);
 assert.equal((html.match(/class="weapon-tile /g)||[]).length,vm.runInContext('mobilePicks().length',h.context));
 assert.doesNotMatch(html,/K\/D|ITEMSHOP_API_KEY|isg_/);
});

test('featured filters and leader choices are driven by publishers rather than hardcoded ranks',()=>{
 const h=loadoutHarness();h.click({featuredCategory:'SMG'});
 assert.equal((h.html().match(/class="weapon-tile /g)||[]).length,2);
 h.click({featuredCategory:'Sniper'});
 assert.equal((h.html().match(/class="weapon-tile /g)||[]).length,1);
 assert.match(h.html(),/KG-7 Vulcan/);
 const alternative=structuredClone(data),entries=alternative.meta.find(b=>b.id==='cod').entries;
 const vel=entries.find(e=>e.weapon==='VEL 46'),iso=entries.find(e=>e.weapon==='ISO Nightshade');
 [vel.rank,iso.rank]=[iso.rank,vel.rank];h.context.alternative=alternative;
 vm.runInContext('state.feed=alternative;state.featuredCategory="SMG";render()',h.context);
 const picks=vm.runInContext('mobilePicks()',h.context);
 assert.equal(picks.find(p=>p.board.id==='cod').entry.weapon,'ISO Nightshade');
});

test('all ten curated weapons open their own workbench and preserve publisher selection',()=>{
 const h=loadoutHarness();
 for(const w of weaponCatalog(data)){
  h.click({source:'wz',page:'weapons',weapon:w.weapon,reveal:'loadout'});
  assert.equal(vm.runInContext('state.weapon',h.context),w.weapon);
  assert.equal(vm.runInContext('state.source',h.context),'wz');
  const html=h.html();
  assert.match(html,/id="weaponLoadout"/);
  assert.ok(html.includes('<h2>'+w.weapon+'</h2>'));
  for(const r of w.rankings)assert.ok(html.includes('#'+r.rank+' <small>'+r.tier));
 }
 assert.equal(h.elements.loadoutDialog.open,true);
});

test('weapon popup preserves the browsing page and gallery mode without an inline workbench',()=>{
 const h=loadoutHarness();h.click({page:'weapons'});h.click({arsenalMode:'all'});
 h.click({page:'brief'});h.click({page:'weapons'});
 assert.equal(vm.runInContext('state.arsenalMode',h.context),'all');
 h.click({page:'brief'});h.click({page:'weapons',weapon:'HAN 86',reveal:'loadout'});
 assert.equal(vm.runInContext('state.page',h.context),'brief');
 assert.equal(h.elements.loadoutDialog.open,true);
 assert.doesNotMatch(h.elements.appMain.innerHTML,/id="weaponLoadout"/);
 assert.match(h.html(),/FSS IS300/);
 assert.equal(h.elements.loadoutDialog.open,true);
});

test('legacy Builds route opens the workbench and alternate builds retain exact attachment values',()=>{
 const h=loadoutHarness();h.click({page:'builds'});
 assert.equal(vm.runInContext('state.page',h.context),'brief');assert.equal(h.elements.loadoutDialog.open,true);
 h.handlers.get('change')({target:{id:'ironSwitch',checked:false}});
 assert.match(h.html(),/data-build="han-meta"/);
 h.click({build:'han-meta'});
 const expected=data.builds.find(b=>b.id==='han-meta');
 for(const [slot,name] of expected.parts)assert.ok(h.html().includes(name),slot+': '+name);
 h.handlers.get('change')({target:{id:'ironSwitch',checked:true}});
 assert.doesNotMatch(h.html(),/data-build="han-meta"/);
 assert.match(h.html(),/FSS IS300/);
});

test('weapons without a published build never fabricate an attachment set',()=>{
 const h=loadoutHarness();h.click({page:'weapons',weapon:'Kastov 762'});
 assert.match(h.html(),/No published build in this snapshot/);
 assert.doesNotMatch(h.html(),/class="attachment"|data-copy=/);
});

test('all 33 catalogue entries and nine category filters preserve official links and illustrative art',()=>{
 const h=loadoutHarness();h.click({page:'weapons'});h.click({arsenalMode:'all'});
 const all=require('../arsenal.js').weapons;
 assert.equal((h.html().match(/class="weapon-tile"/g)||[]).length,33);
 assert.match(h.html(),/not official game imagery/);
 const anchors=[...h.html().matchAll(/<a class="weapon-tile"[^>]*href="([^"]+)"/g)];
 assert.equal(anchors.length,23);for(const a of anchors)assert.equal(a[1],require('../arsenal.js').source);
 for(const category of require('../arsenal.js').categories){
  h.click({arsenalCategory:category});const html=h.html();
  assert.equal((html.match(/class="weapon-tile"/g)||[]).length,all.filter(w=>w.category===category).length,category);
  for(const w of all.filter(w=>w.category===category))assert.ok(html.includes(w.weapon),w.weapon);
 }
 h.click({arsenalCategory:'All'});h.click({arsenalMode:'ranked',page:'weapons',weapon:'Axion',reveal:'loadout'});
 assert.match(h.html(),/id="weaponLoadout"/);
 assert.match(h.html(),/<h2>Axion<\/h2>/);
});

test('both searches match case-insensitively and render explicit empty results',()=>{
 const h=loadoutHarness();h.click({page:'weapons'});h.click({arsenalMode:'all'});
 vm.runInContext('state.arsenalSearch="mOjAvE";render()',h.context);
 assert.equal((h.html().match(/class="weapon-tile"/g)||[]).length,1);
 assert.match(h.html(),/Mojave \.357/);
 vm.runInContext('state.arsenalSearch="not a weapon";render()',h.context);
 assert.match(h.html(),/No weapons match/);
 h.click({arsenalMode:'ranked'});
 vm.runInContext('state.search="axion";render()',h.context);
 assert.equal((h.html().match(/class="weapon-tile /g)||[]).length,1);
 vm.runInContext('state.search="not a weapon";render()',h.context);
 assert.match(h.html(),/No matching weapons/);assert.doesNotMatch(h.html(),/id="weaponLoadout"/);
});

test('patches events and pass preserve every source fact with clear date qualifiers',()=>{
 const h=loadoutHarness();h.click({page:'updates'});
 for(const p of data.patches){assert.ok(h.html().includes(p.title));for(const x of p.bullet)assert.ok(h.html().includes(x.replaceAll('&','&amp;')));}
 h.click({page:'events'});
 for(const e of data.events){assert.ok(h.html().includes(e.title));assert.ok(h.html().includes(e.summary));}
 assert.match(h.html(),/availability unverified/);
 h.click({page:'pass'});
 assert.match(h.html(),/REPORTED START/);
 for(const x of data.battlePass.rewardCategories)assert.ok(h.html().includes(x.replaceAll('&','&amp;')));
 assert.ok(h.html().includes(String(data.battlePass.blackcell.tierSkips)));
 assert.match(h.html(),/OPTIONAL PAID TIER/);
});

test('Store keeps sample labels provider attribution contents official links and unknown prices',()=>{
 const h=loadoutHarness();h.context.sample=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/store.json'),'utf8'));
 vm.runInContext('state.store={data:sample,origin:"dated-example"};render()',h.context);
 assert.match(h.html(),/EXAMPLE · NOT LIVE/);
 h.click({page:'store'});const html=h.html();
 for(const term of ['NOT LIVE','Official bundle details',"What's included",'Data from itemshop.gg','not your personal in-game Store','Platform store'])assert.ok(html.includes(term),term);
 assert.doesNotMatch(html,/ITEMSHOP_API_KEY|isg_/);
});

test('all six navigation destinations still render and mark the active tab',()=>{
 const h=loadoutHarness();
 for(const page of ['brief','weapons','updates','events','pass','store']){
  h.click({page});assert.equal(vm.runInContext('state.page',h.context),page);
  assert.equal((h.elements.bottomNav.innerHTML.match(/<button /g)||[]).length,6);
  assert.ok(h.elements.bottomNav.innerHTML.includes('data-page="'+page+'"'));
  assert.match(h.elements.bottomNav.innerHTML,/aria-current="page"/);
  assert.match(h.html(),/<h1>/);
 }
});

test('presentation escapes untrusted weapon text and preserves offline warning',()=>{
 const h=loadoutHarness();
 const html=vm.runInContext('weaponTile({weapon:"<img src=x onerror=alert(1)>",category:"<script>"})',h.context);
 assert.doesNotMatch(html,/<img src=x|<script>/);assert.match(html,/&lt;img/);
 vm.runInContext('state.offlineCopy=true;render()',h.context);
 assert.match(h.html(),/Offline or previously saved briefing/);
});

test('all ten curated weapons map to original artwork and unknown weapons retain fallback', () => {
 const h=loadoutHarness();
 const cases=[['HAN 86','han-86'],['Axion','axion'],['VEL 46','vel-46'],['ISO Nightshade','iso-nightshade'],['KG-7 Vulcan','kg-7-vulcan'],['Hyeon Burst','hyeon-burst'],['M4','m4'],['Kastov 762','kastov-762'],['X-58 Nyx','x-58-nyx'],['PPSh-41','ppsh-41']];
 for(const [weapon,slug] of cases){
  const art=vm.runInContext('mobileWeaponArt('+JSON.stringify(weapon)+')',h.context);
  assert.match(art,new RegExp('art/featured/'+slug+'\\.webp'));
  assert.match(art,/Original illustrative artwork, not an official/);
  const file=fs.readFileSync(path.join(__dirname,'../art/featured/'+slug+'.webp'));
  assert.equal(file.toString('ascii',0,4),'RIFF');
  assert.equal(file.toString('ascii',8,12),'WEBP');
  assert.ok(file.length<30000,'keep all images light for mobile');
 }
 const fallback=vm.runInContext('mobileWeaponArt("A future unidentified weapon")',h.context);
 assert.match(fallback,/<svg viewBox/);
 assert.doesNotMatch(fallback,/art\/featured\//);
 const html=h.html();
 assert.match(html,/mobile-weapon__illustration/);
 assert.doesNotMatch(html,/1\.42 K\/D/);
});

test('cinematic artwork files have unique identities and retain mobile-size bounds',()=>{
 const crypto=require('node:crypto');
 const all=['han-86','axion','vel-46','iso-nightshade','kg-7-vulcan','hyeon-burst','m4','kastov-762','x-58-nyx','ppsh-41'];
 const hashes=all.map(slug=>{
  const data=fs.readFileSync(path.join(__dirname,'../art/featured',slug+'.webp'));
  assert.equal(data.toString('ascii',0,4),'RIFF',slug);
  assert.equal(data.toString('ascii',8,12),'WEBP',slug);
  assert.ok(data.length>1000 && data.length<15000,slug+' unexpected file size');
  return crypto.createHash('sha256').update(data).digest('hex');
 });
 assert.equal(new Set(hashes).size,10,'all ten weapons should have distinct illustrations');
});

test('closing the loadout restores browsing without leaving inline content',()=>{
 const h=loadoutHarness();h.click({page:'weapons'});
 const before=h.elements.appMain.innerHTML;h.click({weapon:'HAN 86'});
 assert.equal(h.elements.loadoutDialog.open,true);
 assert.equal(h.elements.appMain.innerHTML,before);
 vm.runInContext('closeLoadout()',h.context);
 assert.equal(h.elements.loadoutDialog.open,false);
 assert.equal(h.elements.appMain.innerHTML,before);
});

test('iron-sight changes in the popup preserve the weapon search and background',()=>{
 const h=loadoutHarness();
 vm.runInContext("state.page='weapons';state.search='HAN';render()",h.context);
 const background=h.elements.appMain.innerHTML;
 h.click({weapon:'HAN 86'});
 h.handlers.get('change')({target:{id:'ironSwitch',checked:false}});
 assert.equal(vm.runInContext('state.search',h.context),'HAN');
 assert.equal(h.elements.appMain.innerHTML,background);
 assert.match(h.elements.loadoutContent.innerHTML,/han-meta/);
});
