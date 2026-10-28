# MW4 War Room — Multiplayer Guide

**UI v0.4.0 · editorial data v0.3.0 — October 27, 2026**

A lightweight, installable iPhone home-screen companion for Call of Duty: Modern Warfare 4 multiplayer. It contains only publicly retrievable game information, curated into dated snapshots with direct source links:

- **Overview:** two assault rifle leaders and two SMG leaders, with source-specific rankings and direct loadout links. The home screen also highlights patch notes, events and the Battle Pass using clearer, everyday gaming language.
- **Weapons:** one profile per weapon, combining source-separated CODMunity / WZStats rankings with available attributed loadouts and an iron-sight filter
- **Updates:** source-linked summaries of official multiplayer patch notes
- **Events:** dated event windows sorted by calendar state; unknown end dates remain unverified, and a published time window does not claim in-game availability
- **Pass:** separately accessible Season 1 and BlackCell information, with explicitly qualified dates and unpublished reward tiers
- **Store:** public MW4 web-store data only, with bundle art, included items, source-reported prices, and clear itemshop.gg attribution. Overview has a preview and Store has its own tab. The initial example is explicitly labeled NOT LIVE.

**Not a live external data feed.** The contents of `data/intel.json` were independently reviewed on October 27, 2026. External publishers are not scraped or mirrored on a schedule. Tapping a source link opens the current publisher page, and curated War Room content changes only when this repository is updated. Publisher rankings are not presented as interchangeable universal statistics.

## Install

GitHub Pages deploys from `main` at the repository root. Open the live site in Safari → Share → Add to Home Screen. The service worker caches the application and its last-visited public data for offline access after an online visit; it uses network-first retrieval when connected.

## Data and privacy

War Room v0.3 has no Activision/Xbox sign-in, no automatic personal progression import, no player rank, no manual weapon-level log, and no personal game-stats tracker. It only stores the local **iron-sight filter** and **preferred ranking source** under `mw4-warroom-prefs-v02`. The old v0.1 key (`mw4-warroom-v01`) is not read, overwritten, or deleted by this build; the complete old app is preserved on the `archive/v0.1-working` branch. If revisiting v0.1 in the future, retain the browser's old storage profile.

## Sources and verification

The `data/intel.json` file identifies source URLs and data reviewed dates. Official patch/season content is separated from community ranking/build recommendations. Dates reported by third parties are labeled accordingly, especially the November 6 Season 1 date and Boot Camp end date. No published attachment is claimed to be unlocked for a particular user.

Before publishing a new briefing, check primary official patch notes and events, verify multiple multiplayer-only ranking sources, update source and reviewed timestamps, and validate against screenshots/source pages. Keep Warzone and DMZ rankings separate.

## Local validation

Run a static server from the repository root and load the site with a modern browser. The shipped app has no third-party scripts or external runtime dependencies; it loads `logic.js`, `app.js` and `data/intel.json` from the same host. Test on mobile viewport for navigation, ranking-source/category filters, sight preference, build copy, source links, season tabs, accessibility, and offline fallback after one online visit.

Fan project; not affiliated with Activision or Infinity Ward.

## Editorial reliability pipeline (v0.3.0)

War Room has a **daily GitHub Actions editorial watchdog** (10:17 AM America/New_York) and a separate schema/test workflow on repository changes. Standard GitHub-hosted runners in this public repository are free under GitHub's published Actions policy. Scheduled runs are best-effort (not real-time) and GitHub can disable schedules on an inactive public repository after 60 days; verify run history if updates stop.

- `scripts/validate_intel.py` checks the entire JSON schema, source identity, HTTPS links, ranking scopes, weapon builds and their optic flags, source references, patch ordering, multiplayer scope, event dates and Battle Pass values. Invalid data fails CI.
- `scripts/review_watch.py` checks **only** the age of each editorial section and upcoming event/Battle Pass deadlines. It creates a Markdown report. `scripts/sync_review_issue.py` keeps **one** GitHub Issue for overdue reviews, rather than sending daily duplicate issues. It closes the issue once a *real* editorial review brings all sections back within limits.
- Review limits are fixed in `reviewLimitsDays`: meta 3 days, builds 10, patches 3, events 2, Battle Pass 4. Section dates in `reviewedSections` do not advance automatically; they can be updated **only after someone has checked actual publisher material**. The app independently labels outdated sections and preserves a last-validated browser copy if an update fails.
- **No external data is scraped, mirrored or silently reinterpreted.** CODMunity and WZStats are not unattended feeds. This pipeline does not detect new official patch notes or auto-import them. Automated ingestion needs a separately verified authorized feed and data-contract review.
- Review issues are **public GitHub Issues**, and contain only public game-data dates and source references, not player information.

### Publish a reviewed update

1. Check current publisher pages manually, official Activision notes first. Distinguish Multiplayer vs Warzone/DMZ and editorial rankings vs actual balance patches.
2. Edit `data/intel.json` and only the `reviewedSections` keys for sections you truly inspected. Set `reviewed` to the publication date. Do not update dates to make freshness badges go green without reviewing the source.
3. Run `python3 scripts/validate_intel.py`, `python3 -m unittest discover -s tests -v`, and `node --check app.js`.
4. Commit a validated update to `main`, which deploys through existing GitHub Pages. The validation workflow reports failures but is **not a configured protected-branch gate**; use a preview branch or PR for higher-risk edits.
5. Roll back by restoring the last known-good commit or `archive/v0.2-validated-20261027`. The site displays older reviewed dates instead of pretending a rollback is current.

The old `archive/v0.1-working` and `archive/v0.2-validated-20261027` branches remain available. v0.1 browser data remains untouched. The public last-validated briefing remains in a cache key separate from account/progression data. The initial working v0.2.1 is preserved in `archive/v0.2.1-validated-20261027`.

## Safer release process (v0.3)

1. Create a feature branch from `main` and open a PR. Wait for **Validate curated data and app syntax** (Python schema/test suite and JavaScript weapon/event logic tests) to pass before merging. `Review War Room intelligence` also performs a dry run on PRs and ordinary pushes; issue writes only occur in the scheduled job.
2. Merge only after both checks pass. This repository currently uses a **branch-based Pages publishing source**, which publishes any `main` change. Therefore, a PR-only release process is practiced but **not enforced** by the deployment source until the repository owner enables branch protection.
3. For an enforceable main-branch gate, configure GitHub **Settings → Branches → Add branch protection rule** for `main`, enable **Require a pull request before merging** (do not require external approvals in a one-person project), and **Require status checks to pass**, selecting **Validate curated data and app syntax**. Only then treat the rule as enforced; the connected GitHub app cannot edit repository administration settings.
4. The last working snapshots remain on archive branches. Roll back by restoring the prior validated commit if necessary.

The **daily review watchdog is not a live feed**. It reports overdue section dates and links directly to official/community source pages for a human to verify, never claims to have downloaded fresh rankings, and never changes review timestamps automatically. Its first actual scheduled execution remains a separate validation milestone. The run invoked by PR or push is a safe dry run; the scheduled job alone can maintain a public review issue.

## Publisher announcement leads through Steam (candidate monitor)

Steamworks documents a **public, no-account-key** ISteamNews/GetNewsForApp/v2 endpoint. War Room checks the **Call of Duty Steam application, 1938090**, daily at 10:27 AM America/New_York using this published interface. An October 27 GitHub PR probe successfully read 40 entries, 25 mentioning MW4. This is **not** a promise that all MW4 patch notes, events, or Battle Pass information will appear there, and the feed also includes unrelated Call of Duty games.

The scheduled workflow reads **title, publication date, and URL only**, filters for potentially relevant MW4 updates, and opens/updates **one GitHub review issue** when an entry is newer than that section's editorial review date. It never reproduces article bodies, scrapes Activision/CODMunity/WZStats pages, writes player data, or automatically changes the live JSON. Entries are **unverified leads** until the original source and multiplayer relevance are checked by a person. The issue is deliberately not auto-closed; it is closed after real review. A news announcement edited without changing its date may escape detection, and headlines can be edited without modifying their title, URL or timestamp. The monitor now includes announcements dated on the **same calendar day** as the last editorial review (conservative, because exact review times are unknown) and remembers previously alerted announcement **IDs, exact UTC timestamps and headline fingerprints** inside the review issue. Unchanged repeats do not update the issue; new or renamed candidates add to the checklist without removing earlier manual checkmarks.

The workflow has a manual trigger and PR dry-run probe. A live scheduled run and the issue-writing path remain **unverified** until observed. API timeouts/errors fail the check safely without modifying the website or erasing its last validated data.

Official Valve API reference: https://partner.steamgames.com/doc/webapi/ISteamNews?language=english


### GitHub issue-write smoke test

The one-shot GitHub Actions workflow `.github/workflows/alert-issue-smoke.yml` is triggered when that workflow file is first merged into `main` (and can also be run manually). It creates a distinctly titled **TEST** GitHub issue, edits it, verifies the edit, and closes it automatically. This validates GitHub Actions `issues: write` permissions and creates a closed public audit record. The smoke test is independent of Steam news and does **not** claim that a real scheduled alert has fired. Regular monitoring still runs at its configured times.

## MW4 public Store setup (requires a one-time API key)

The Store uses itemshop.gg's documented free Call of Duty JSON API:
https://itemshop.gg/developers . It is not Activision, not a personal account
integration and not the entire in-game Store.

1. Visit https://itemshop.gg/account#api . Sign in with Discord and create
   a key called "War Room" for this website.
2. In the War Room repository open **Settings → Secrets and variables → Actions
   → New repository secret** at:
   https://github.com/zy65h95wjn-netizen/mw4-war-room/settings/secrets/actions
   Name the secret **ITEMSHOP_API_KEY**, paste your key and click Add secret.
   Never paste the key into a chat, issue, source file or browser console.
3. Open repository **Actions → Refresh MW4 public Store data → Run workflow**
   (branch main) for the first sync. It also runs automatically at 03:37,
   09:37, 15:37 and 21:37 UTC every day (best effort).
4. After success, refresh the app; the Store changes from a dated EXAMPLE
   to a checked public-source listing.

### Data and security boundaries

- GitHub Actions sends the private API key in an Authorization header to
  https://itemshop.gg/api/v1/shop/call-of-duty. The iPhone/browser never
  contacts that authenticated endpoint or receives the key.
- scripts/refresh_store.py only accepts the "Modern Warfare 4" section,
  excludes BO7-only bundles, validates fields, and publishes a restricted
  display projection to data/store.json on the separate public store-feed
  branch. Protected main and curated weapon/patch data are untouched.
- The website reads sanitized public JSON from that branch and checks schema,
  allowed links, timestamps and source attribution. It keeps a last-good
  browser copy for offline use. A provider failure does not overwrite data.
- If the key is missing, the workflow clearly says "not configured" and
  does not contact the provider. The app shows a dated documentation
  example with a prominent NOT LIVE label; this is never shown as current.
- Unknown prices and "Platform store" are not free. No invented USD or
  COD Point conversions are made.
- A visible "Data from itemshop.gg" link is required on every Store
  display; external images may be loaded from the provider's artwork CDN.
- This is the public web-store selection, not personalized inventory.
  Availability and price may differ on Xbox PC and in the actual game.

### Rollback

All UI changes use a passing pull request. The pre-Store milestone is
archived on branch archive/20261027-before-store. The separate
store-feed branch contains no secrets. Revoking the key or disabling the
workflow stops automatic updates without breaking other War Room sections.
