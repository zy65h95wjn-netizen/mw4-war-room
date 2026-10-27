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

test('briefing View attachments opens the HAN 86 loadout and reveals the profile', () => {
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
