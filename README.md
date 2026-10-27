# MW4 War Room — Multiplayer Intelligence

**v0.2.0 — October 27, 2026**

A lightweight, installable iPhone home-screen companion for Call of Duty: Modern Warfare 4 multiplayer. It contains only publicly retrievable game information, curated into dated snapshots with direct source links:

- **Brief:** key ranking differences, a source-linked iron-sight build, latest patch and season highlights
- **Meta:** CODMunity and WZStats multiplayer rankings displayed separately (with their different ranking scopes)
- **Builds:** a small set of published, attributed attachment recommendations; "Iron sights first" enabled by default
- **Updates:** source-linked summaries of official multiplayer patch notes
- **Season:** events, time-limited modes, rewards and explicitly qualified Battle Pass / BlackCell announcements

**Not a live external data feed.** The contents of `data/intel.json` were independently reviewed on October 27, 2026. External publishers are not scraped or mirrored on a schedule. Tapping a source link opens the current publisher page, and curated War Room content changes only when this repository is updated. Publisher rankings are not presented as interchangeable universal statistics.

## Install

GitHub Pages deploys from `main` at the repository root. Open the live site in Safari → Share → Add to Home Screen. The service worker caches the application and its last-visited public data for offline access after an online visit; it uses network-first retrieval when connected.

## Data and privacy

War Room v0.2 has no Activision/Xbox sign-in, no automatic personal progression import, no player rank, no manual weapon-level log, and no personal game-stats tracker. It only stores the local **iron-sight filter** and **preferred ranking source** under `mw4-warroom-prefs-v02`. The old v0.1 key (`mw4-warroom-v01`) is not read, overwritten, or deleted by this build; the complete old app is preserved on the `archive/v0.1-working` branch. If revisiting v0.1 in the future, retain the browser's old storage profile.

## Sources and verification

The `data/intel.json` file identifies source URLs and data reviewed dates. Official patch/season content is separated from community ranking/build recommendations. Dates reported by third parties are labeled accordingly, especially the November 6 Season 1 date and Boot Camp end date. No published attachment is claimed to be unlocked for a particular user.

Before publishing a new briefing, check primary official patch notes and events, verify multiple multiplayer-only ranking sources, update source and reviewed timestamps, and validate against screenshots/source pages. Keep Warzone and DMZ rankings separate.

## Local validation

Run a static server from the repository root and load the site with a modern browser. The shipped app has no third-party scripts or external runtime dependencies; it loads `app.js` and `data/intel.json` from the same host. Test on mobile viewport for navigation, ranking-source/category filters, sight preference, build copy, source links, season tabs, accessibility, and offline fallback after one online visit.

Fan project; not affiliated with Activision or Infinity Ward.