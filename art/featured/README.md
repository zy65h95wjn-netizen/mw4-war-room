# War Room original illustrative weapon artwork

This directory contains **original conceptual illustrations**, not official Modern Warfare 4 renders, exact weapon geometry, or evidence of attachments/stats.

## Validated artwork — v0.4.3
- HAN 86 — `han-86.webp`
- Axion — `axion.webp`
- VEL 46 — `vel-46.webp`
- ISO Nightshade — `iso-nightshade.webp`

Those four assets were tested on an iPhone and approved.

## Approved artwork expansion — v0.4.4
- KG-7 Vulcan — `kg-7-vulcan.webp`
- Hyeon Burst — `hyeon-burst.webp`
- M4 — `m4.webp`
- Kastov 762 — `kastov-762.webp`
- X-58 Nyx — `x-58-nyx.webp`
- PPSh-41 — `ppsh-41.webp`

The six additional pieces are separately exported crops from original AI-generated cinematic concept artwork, with cool-blue industrial atmosphere and warm amber highlights to match the established visual direction. All six were individually cropped to remove the collage labels and borders, compressed to 220 × 89 WebP (2.5–3.2 KB each), and SHA-verified before commit. They are stylized illustrations, not exact in-game models or evidence of weapon specifications. The KG-7 imagery is conceptual and must not be treated as proof of its mechanical design.

Assets are lightweight local WebP files, loaded using a strictly enumerated mapping in `app.js`. Non-catalog weapons still fall back to a generic SVG, with no third-party images or API calls. They never affect rankings, store, loadouts, or player progression.

**Release review:** The user visually approved the corrected six-weapon iPhone preview on October 28, 2026. Merge is gated on passing GitHub checks. The validated v0.4.3 release remains the rollback point. Final real-device rendering must be checked after deployment; the visual preview alone does not prove the live iPhone layout.

## Full launch arsenal — approved for v0.4.5

Activision's official October 19, 2026 MW4 launch guide lists **33 launch weapons** (24 primary, 8 secondary, 1 melee). All 33 names and category classifications are recorded in `arsenal.js`, **separate** from curated source rankings in `data/intel.json`. Existing ten individual illustration files remain byte-for-byte unchanged.

The **23 additional conceptual illustrations** are supplied through `full-arsenal-atlas.webp` (a 5-column, 5-row WebP sprite; 23 occupied cells). The sprites were created from new original AI-generated fictional weapon renderings, optimized for small iPhone cards and compressed to approximately 24 KB total. The site never downloads original game artwork from Activision. Their shapes are illustrations, **not claimed accurate in-game weapon geometry**. Existing artwork fallback remains available for unknown future names.

The gallery's "Official reference" links refer only to the **weapon names and categories** in Activision's primary source, not to licensed art or publisher-authored rankings. The official source has contradictory unlock levels in some sections, so the full catalogue deliberately does not display any unlock-level claims.

**Approval and validation:** The user visually approved the 33-weapon gallery and its original artwork on October 28, 2026. All required PR checks must remain successful before merge. After GitHub Pages deployment, verify the live iPhone display and weapon navigation. The validated v0.4.4 commit `f12a7d88e714eaa535d6ccef20ca04da279b030d` remains the recoverable rollback point.
