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
  assert.ok(han.rankings.some(r => r.board === 'cod'));
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
    appMain: { innerHTML: '' },
    bottomNav: { innerHTML: '' },
    overlay: { hidden: true, addEventListener() {} },
    toast: { textContent: '', classList: { add() {}, remove() {} } }
  };
  const document = {
    getElementById(id) {
      if (id === 'weaponLoadout') {
        return elements.appMain.innerHTML.includes('id="weaponLoadout"')
          ? { scrollIntoView() { reveals++; } } : null;
      }
      return elements[id] || null;
    },
    addEventListener(type, fn) { handlers.set(type, fn); }
  };
  const app = fs.readFileSync(path.join(__dirname, '../app.js'), 'utf8');
  const bootIndex = app.lastIndexOf('\nboot();\n');
  assert.ok(bootIndex > 0, 'boot invocation marker must exist');
  const context = vm.createContext({
    console, document, window: { scrollTo() {} },
    navigator: { onLine: true }, localStorage: { getItem() { return null; }, setItem() {} },
    WarRoomLogic: require('../logic.js'), setTimeout, clearTimeout
  });
  vm.runInContext(app.slice(0, bootIndex), context, { filename: 'app.js' });
  context.testIntel = data;
  vm.runInContext('state.feed=testIntel; bindEvents(); render();', context);
  function click(dataset) {
    const button = { id: '', dataset };
    handlers.get('click')({ target: { closest(selector) { assert.equal(selector, 'button'); return button; } } });
  }
  return { elements, context, click, reveals: () => reveals, handlers };
}

test('meta leader opens the HAN 86 loadout and reveals the profile', () => {
  const h = loadoutHarness();
  assert.ok(h.elements.appMain.innerHTML.includes('data-page="weapons" data-weapon="HAN 86" data-reveal="loadout"'));
  h.click({ page: 'weapons', weapon: 'HAN 86', reveal: 'loadout' });
  assert.equal(vm.runInContext('state.page', h.context), 'weapons');
  assert.equal(vm.runInContext('state.weapon', h.context), 'HAN 86');
  assert.match(h.elements.appMain.innerHTML, /id="weaponLoadout"/);
  assert.match(h.elements.appMain.innerHTML, /Attachment slots/);
  assert.equal(h.reveals(), 1);
});

test('choosing another weapon actually reveals that weapon’s attachments', () => {
  const h = loadoutHarness();
  h.click({ page: 'weapons' });
  h.click({ weapon: 'Axion' });
  assert.equal(vm.runInContext('state.weapon', h.context), 'Axion');
  assert.match(h.elements.appMain.innerHTML, /Attachment slots/);
  assert.equal(h.reveals(), 1);
});

test('legacy Builds route no longer silently loops back to briefing', () => {
  const h = loadoutHarness();
  h.click({ page: 'builds' });
  assert.equal(vm.runInContext('state.page', h.context), 'weapons');
  assert.match(h.elements.appMain.innerHTML, /Recommended attachments/);
  assert.equal(h.reveals(), 1);
});

test('iron-sight switch and alternate loadout selection remain functional', () => {
  const h = loadoutHarness();
  h.click({ page: 'weapons', weapon: 'HAN 86' });
  h.handlers.get('change')({ target: { id: 'ironSwitch', checked: false } });
  assert.ok(h.elements.appMain.innerHTML.includes('data-build="han-meta"'));
  h.click({ build: 'han-meta' });
  assert.equal(vm.runInContext('state.buildId', h.context), 'han-meta');
  assert.match(h.elements.appMain.innerHTML, /Attachment slots/);
});

test('the overview replaces marketing and duplicate spotlight with practical updates', () => {
  const h = loadoutHarness();
  const body = h.elements.appMain.innerHTML;
  assert.match(body, /class="brief-mast"/);
  assert.match(body, /Overview/);
  assert.match(body, /LAST REVIEW/);
  assert.match(body, /Top Weapons/);
  assert.match(body, /Latest Updates/);
  assert.match(body, /PATCH NOTES/);
  assert.match(body, /EVENTS/);
  assert.match(body, /BATTLE PASS/);
  assert.match(body, /not live rankings/);
  assert.doesNotMatch(body, /Know the meta|Own the lobby|Loadout spotlight|NO ACCOUNT SYNC|VIEW ATTACHMENTS/i);
  const style = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
  assert.match(style, /\.brief-mast\{/);
  assert.match(style, /\.leader-card\{/);
  assert.match(style, /\.intel-grid\{/);
  assert.match(style, /@media\(max-width:399px\)/);
});

test('the WZStats meta leader opens Axion and its sourced no-optic build', () => {
  const h = loadoutHarness();
  const before = h.elements.appMain.innerHTML;
  assert.match(before, /data-source="wz" data-page="weapons" data-weapon="Axion" data-reveal="loadout"/);
  h.click({ source: 'wz', page: 'weapons', weapon: 'Axion', reveal: 'loadout' });
  assert.equal(vm.runInContext('state.page', h.context), 'weapons');
  assert.equal(vm.runInContext('state.source', h.context), 'wz');
  assert.equal(vm.runInContext('state.weapon', h.context), 'Axion');
  assert.match(h.elements.appMain.innerHTML, /Recommended attachments/);
  assert.match(h.elements.appMain.innerHTML, /id="weaponLoadout"/);
  assert.equal(h.reveals(), 1);
});

test('patch, event and Battle Pass intelligence cards all open their destinations', () => {
  const h = loadoutHarness();
  for (const [page, term] of [['updates','Patch Notes'], ['events','Events'], ['pass','Battle Pass']]) {
    h.click({ page });
    assert.equal(vm.runInContext('state.page', h.context), page);
    assert.ok(h.elements.appMain.innerHTML.includes(term), page + ' content did not open');
    h.click({ page: 'brief' });
  }
});

test('briefing dates and weapon rankings still come from the existing sourced snapshot', () => {
  const h = loadoutHarness();
  const body = h.elements.appMain.innerHTML;
  assert.ok(body.includes('CODMunity'));
  assert.ok(body.includes('WZStats'));
  assert.ok(body.includes('HAN 86'));
  assert.ok(body.includes('Axion'));
  assert.ok(body.includes('Oct 27'));
  assert.ok(body.includes('Official patch notes'));
});


test('brief meta leaders render two source-specific ARs then two source-specific SMGs', () => {
  const h = loadoutHarness();
  const body = h.elements.appMain.innerHTML;
  const cards = [...body.matchAll(/<button[^>]*class="leader-card[^"]*"[^>]*data-source="(cod|wz)"[^>]*data-page="weapons"[^>]*data-weapon="([^"]+)"[^>]*data-reveal="loadout"[^>]*data-weapon-group="(AR|SMG)"/g)]
    .map(x => [x[1],x[2],x[3]]);
  assert.deepEqual(cards, [
    ['cod','HAN 86','AR'],
    ['wz','Axion','AR'],
    ['cod','VEL 46','SMG'],
    ['wz','ISO Nightshade','SMG']
  ]);
  assert.ok(body.indexOf('ASSAULT RIFLES') < body.indexOf('SUBMACHINE GUNS'));
  assert.equal((body.match(/class="brief-leaders"/g) || []).length, 2);
  assert.match(body, /#2 Overall/);
  assert.match(body, /#1 SMG/);
  assert.match(body, /Sources rank weapons differently/);
});

test('both SMG meta cards open the correct sourced weapon loadouts', () => {
  const h = loadoutHarness();
  for (const [source,weapon] of [['cod','VEL 46'],['wz','ISO Nightshade']]) {
    h.click({page:'weapons',source,weapon,reveal:'loadout',weaponGroup:'SMG'});
    assert.equal(vm.runInContext('state.page',h.context),'weapons');
    assert.equal(vm.runInContext('state.weapon',h.context),weapon);
    assert.equal(vm.runInContext('state.source',h.context),source);
    assert.match(h.elements.appMain.innerHTML,/id="weaponLoadout"/);
    assert.match(h.elements.appMain.innerHTML,/Attachment slots/);
  }
  assert.equal(h.reveals(),2);
});

test('leader picks are derived from publisher rankings and not from a hardcoded weapon list', () => {
  const h = loadoutHarness();
  const alternative = structuredClone(data);
  const board = alternative.meta.find(x => x.id === 'cod');
  const vel = board.entries.find(x=>x.weapon==='VEL 46');
  const iso = board.entries.find(x=>x.weapon==='ISO Nightshade');
  const before = vel.rank;
  vel.rank = iso.rank;
  iso.rank = before;
  h.context.testIntel = alternative;
  vm.runInContext('state.feed=testIntel;state.page="brief";render()',h.context);
  const matches = [...h.elements.appMain.innerHTML.matchAll(/data-source="cod" data-page="weapons" data-weapon="([^"]+)" data-reveal="loadout" data-weapon-group="SMG"/g)];
  assert.equal(matches.length,1);
  assert.equal(matches[0][1],'ISO Nightshade');
});

test('two-row meta leaders retain readable responsive layout rules', () => {
  const style = fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
  assert.match(style,/\.brief-leader-category\{/);
  assert.match(style,/\.brief-leader-group\+\.brief-leader-group\{/);
  assert.match(style,/\.brief-leaders\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(style,/\.leader-card__weapon\{overflow-wrap:break-word/);
  assert.match(style,/@media\(max-width:399px\)/);
});

test('plain-language navigation and rankings keep source-specific positions', () => {
  const h=loadoutHarness();
  const overview=h.elements.appMain.innerHTML;
  assert.match(h.elements.bottomNav.innerHTML,/>Overview<\/button>/);
  assert.match(overview,/#1 Overall/);
  assert.match(overview,/#2 Overall/);
  assert.match(overview,/#1 Assault Rifle/);
  assert.match(overview,/#1 SMG/);
  assert.match(overview,/2 RANKING SOURCES/);
  assert.match(overview,/MW4 MULTIPLAYER/);
  assert.match(overview,/Weapons, builds, updates, and events/);
});

test('weapons, patches, events and pass pages all use clear gaming copy', () => {
  const h=loadoutHarness();
  for(const [page,expected] of [
    ['weapons','Weapons & Loadouts'],
    ['updates','GAME UPDATES'],
    ['events','EVENTS & REWARDS'],
    ['pass','SEASON DETAILS']
  ]) {
    h.click({page});
    const html=h.elements.appMain.innerHTML;
    assert.ok(html.includes(expected),page+' lacks expected heading '+expected);
    assert.doesNotMatch(html,/THE INTELLIGENCE ARMORY|THE CHANGE LOG|OPERATIONS DESK|SEASON INTELLIGENCE/);
  }
  h.click({page:'brief'});
  assert.doesNotMatch(h.elements.appMain.innerHTML,/FIELD BRIEF|FIELD INTEL|Latest intelligence|Meta leaders|OPERATIONS/);
});
