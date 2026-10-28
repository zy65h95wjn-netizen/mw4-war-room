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
