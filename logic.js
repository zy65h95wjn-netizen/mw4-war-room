/* MW4 War Room: pure, testable client-side data joins and event windows. */
(function (root) {
  'use strict';
  const SECTION_ORDER = ['AR', 'SMG', 'LMG', 'Shotgun', 'Marksman', 'Sniper', 'Pistol', 'Launcher', 'Melee'];

  function weaponCatalog(data) {
    const result = new Map();
    function ensure(weapon, category) {
      let item = result.get(weapon);
      if (!item) {
        item = { weapon, category, rankings: [], builds: [] };
        result.set(weapon, item);
      } else if (item.category !== category) {
        throw new Error(`Conflicting weapon category: ${weapon}`);
      }
      return item;
    }
    for (const board of data.meta || []) {
      for (const entry of board.entries || []) {
        ensure(entry.weapon, entry.category).rankings.push({
          source: board.source, board: board.id, boardName: board.name,
          rank: entry.rank, tier: entry.tier, type: board.rankingType,
          updated: board.updated
        });
      }
    }
    for (const build of data.builds || []) {
      ensure(build.weapon, build.category).builds.push(build);
    }
    return Array.from(result.values()).sort((a, b) => {
      const categoryDiff = SECTION_ORDER.indexOf(a.category) - SECTION_ORDER.indexOf(b.category);
      return categoryDiff || a.weapon.localeCompare(b.weapon);
    });
  }

  function dayKey(date) {
    return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
  }

  function eventTiming(event, now = new Date()) {
    const today = dayKey(now);
    const reported = event.scheduleConfidence !== 'official';
    if (event.ends && today > event.ends) {
      return { kind: 'ended', label: 'Listed window ended', order: 3 };
    }
    if (today < event.starts) {
      return { kind: 'upcoming', label: reported ? 'Upcoming · reported' : 'Upcoming · announced', order: 0 };
    }
    if (!event.ends) {
      return { kind: 'unconfirmed', label: 'Started · availability unverified', order: 2 };
    }
    return {
      kind: 'window',
      label: reported ? 'Within reported window' : 'Within announced window',
      order: 1
    };
  }

  function orderedEvents(events, now = new Date()) {
    return [...events].sort((a, b) => {
      const aStatus = eventTiming(a, now), bStatus = eventTiming(b, now);
      return aStatus.order - bStatus.order || a.starts.localeCompare(b.starts);
    });
  }

  const exports = { weaponCatalog, dayKey, eventTiming, orderedEvents };
  if (typeof module !== 'undefined' && module.exports) module.exports = exports;
  else root.WarRoomLogic = exports;
})(typeof globalThis !== 'undefined' ? globalThis : this);