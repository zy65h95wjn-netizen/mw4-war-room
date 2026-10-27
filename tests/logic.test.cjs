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