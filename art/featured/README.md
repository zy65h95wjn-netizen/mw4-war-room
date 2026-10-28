# War Room original illustrative weapon artwork

This directory contains **original conceptual illustrations**, not official Modern Warfare 4 renders, exact weapon geometry, or evidence of attachments/stats.

## Validated artwork — v0.4.3
- HAN 86 — `han-86.webp`
- Axion — `axion.webp`
- VEL 46 — `vel-46.webp`
- ISO Nightshade — `iso-nightshade.webp`

Those four assets were tested on an iPhone and approved.

## Proposed expansion — review branch only
- KG-7 Vulcan — `kg-7-vulcan.webp`
- Hyeon Burst — `hyeon-burst.webp`
- M4 — `m4.webp`
- Kastov 762 — `kastov-762.webp`
- X-58 Nyx — `x-58-nyx.webp`
- PPSh-41 — `ppsh-41.webp`

The six additional pieces are cropped and adapted from original AI-generated concept art, with visual variations appropriate to each weapon class. They deliberately do not claim to reproduce the exact in-game firearm models. The classic PPSh concept uses additional custom illustration edits.

Assets are lightweight local WebP files, loaded using a strictly enumerated mapping in `app.js`. Non-catalog weapons still fall back to a generic SVG, with no third-party images or API calls. They never affect rankings, store, loadouts, or player progression.

**Review gate:** keep this branch unmerged until the user approves the actual iPhone rendering. The validated v0.4.3 main branch is the rollback point.
