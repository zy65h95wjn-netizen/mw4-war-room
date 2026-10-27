# War Room editorial pipeline

This is the **review-to-publish** procedure for the MW4 multiplayer intelligence database. It does not scrape community meta sites, request player account credentials, or automatically republish unverified articles.

## 1. Detection: discovery, not proof

- Steam's public announcement metadata generates *possible* MW4 leads in a deduplicated GitHub Issue. Other Call of Duty titles also appear in the feed.
- The existing editorial watchdog reports data that is due for review by age. It does not know whether the publisher changed anything.
- New leads can also be submitted using **Issues → New issue → Verify a War Room update**.

## 2. Verification: inspect the original source

For official patch facts, read the Activision patch article, check the exact **MW4 Multiplayer** scope, date, and details. For Battle Pass or events, distinguish confirmed facts from community-reported dates and unavailable reward lists. For community rankings or weapon builds, attribute the publisher, do not invent a consensus or infer a game patch, and respect reuse restrictions.

If the real source cannot be verified, keep the lead in an Issue; **do not update the app**.

## 3. Prepare a candidate pull request

Use a new branch and update only the affected portion of `data/intel.json`. For **each** changed content section (`meta`, `builds`, `patches`, `events`, `battlePass`), append one new source-review receipt in `editorial/reviews.json`. For changes to the source URL catalog, append an additional `sources` receipt. Historical receipts must never be rewritten.

Example receipt for a *hypothetical* original Activision article (change the source ID, date, note and content based on the actual verification):

```json
{
  "id": "review-patches-2026-10-28-one",
  "section": "patches",
  "checkedAt": "2026-10-28",
  "reviewType": "official-confirmed",
  "method": "human-source-review",
  "sourceIds": ["officialPatch"],
  "evidenceNote": "Read the original dated Activision patch notes; checked multiplayer-specific statements, publication date and affected features."
}
```

Rankings and builds use `reviewType: "community-reported"` with the actual community source ID. The receipt source ID must already exist in the new JSON file. For official patch claims, at least one original Activision source is required. Source-review receipts document accountability; **they are not independent proof that the linked page supports the claim**.

Advance only the corresponding `reviewedSections` date to the receipt's actual checked date, and ensure the overall `reviewed` date is not earlier than any newly checked date. Do not update unrelated freshness dates.

## 4. PR checks and publishing

Open a normal pull request against protected `main`. The required check **Validate curated data and app syntax** runs the existing content tests and the new editorial evidence gate. It rejects:
- any change to published sections or their freshness dates without a new receipt;
- missing or unrecognized source IDs, fake automated review methods, or unofficial sources labeled as confirmed patch facts;
- deletion or rewriting of prior receipts, unsupported source changes, and future-dated review metadata.

A real reviewer must still inspect the original source. Merge only once the PR's status check passes and content is editorially verified; GitHub Pages then deploys the updated intel. Never promote a headline automatically.

The existing browser cache preserves the last usable locally validated briefing when a subsequent data fetch fails. Earlier releases also remain accessible in archive branches.

## Why not auto-open bot PRs?

GitHub's built-in `GITHUB_TOKEN` can generate approval-required PR workflows, and pushes made with it do not normally trigger downstream builds. A standard editor-created PR avoids bot approval traps and maintains the human fact-checking boundary. No external API tokens or paid services are required for this workflow.
