"""Regression tests for War Room's human-reviewed editorial release gate."""
import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from editorial_gate import check_change, ReviewGateError

DAY0, DAY1 = "2026-10-27", "2026-10-28"
TODAY = date(2026, 10, 28)


def baseline():
    return {
        "schema": 2, "coverage": "Modern Warfare 4 multiplayer only",
        "release": "0.3.0", "reviewed": DAY0,
        "reviewedSections": {x: DAY0 for x in ("meta", "builds", "patches", "events", "battlePass")},
        "sources": [
            {"id": "act", "url": "https://www.callofduty.com/patchnotes/test", "class": "Official"},
            {"id": "cod", "url": "https://codmunity.gg/mw4", "class": "Community"},
        ],
        "meta": [{"id": "m", "source": "cod"}],
        "builds": [{"id": "b", "source": "cod"}],
        "patches": [{"title": "Prior patch", "source": "act"}],
        "events": [{"title": "Prior event", "source": "act"}],
        "battlePass": {"status": "unpublished", "source": "act"},
    }


def ledger(items=None):
    return {"schema": 1, "reviews": items or []}


def receipt(section, when=DAY1, kind=None, src=None):
    kind = kind or ("community-reported" if section in ("meta", "builds") else "official-confirmed")
    return {
        "id": f"review-{section.lower()}-{when}", "section": section,
        "checkedAt": when, "reviewType": kind, "method": "human-source-review",
        "sourceIds": [src or ("cod" if kind == "community-reported" else "act")],
        "evidenceNote": "Read the original article, checked game mode, timing and claim against its actual contents.",
    }


class EditorialReviewTests(unittest.TestCase):
    def setUp(self):
        self.before = baseline()
        self.after = copy.deepcopy(self.before)
        self.old = ledger()
        self.new = ledger()

    def check(self):
        return check_change(self.before, self.after, self.old, self.new, TODAY)

    def change(self, section="patches", when=DAY1):
        if isinstance(self.after[section], list):
            self.after[section].append({"title": "Verified change"})
        else:
            self.after[section]["status"] = "announced"
        self.after["reviewedSections"][section] = when
        self.after["reviewed"] = when
        self.new["reviews"].append(receipt(section, when))

    def test_no_change_needs_no_receipt(self):
        self.assertEqual(self.check(), [])

    def test_verified_patch_passes(self):
        self.change()
        self.assertEqual(self.check(), ["patches"])

    def test_attributed_meta_passes(self):
        self.change("meta")
        self.assertEqual(self.check(), ["meta"])

    def test_changed_section_without_receipt_fails(self):
        self.change()
        self.new = ledger()
        with self.assertRaises(ReviewGateError): self.check()

    def test_date_refresh_without_receipt_fails(self):
        self.after["reviewedSections"]["events"] = DAY1
        with self.assertRaises(ReviewGateError): self.check()

    def test_one_receipt_cannot_refresh_two_sections(self):
        self.change("patches")
        self.after["reviewedSections"]["events"] = DAY1
        with self.assertRaises(ReviewGateError): self.check()

    def test_receipt_date_must_match_freshness(self):
        self.change()
        self.new["reviews"][0]["checkedAt"] = DAY0
        with self.assertRaises(ReviewGateError): self.check()

    def test_unrecognized_source_fails(self):
        self.change()
        self.new["reviews"][0]["sourceIds"] = ["no-such-id"]
        with self.assertRaises(ReviewGateError): self.check()

    def test_patch_claim_cannot_be_only_community(self):
        self.change()
        self.new["reviews"][0]["reviewType"] = "community-reported"
        self.new["reviews"][0]["sourceIds"] = ["cod"]
        with self.assertRaises(ReviewGateError): self.check()

    def test_official_claim_requires_activision_source(self):
        self.change()
        self.new["reviews"][0]["sourceIds"] = ["cod"]
        with self.assertRaises(ReviewGateError): self.check()

    def test_steam_headline_is_not_human_review(self):
        self.change()
        self.new["reviews"][0]["method"] = "steam-headline"
        with self.assertRaises(ReviewGateError): self.check()

    def test_future_review_date_fails(self):
        self.change()
        self.new["reviews"][0]["checkedAt"] = "2027-01-01"
        with self.assertRaises(ReviewGateError): self.check()

    def test_prior_receipt_cannot_be_changed(self):
        old = receipt("events", DAY0)
        self.old = ledger([old])
        self.new = ledger([dict(old, evidenceNote="This once-published editorial receipt is being silently rewritten, which is forbidden.")])
        with self.assertRaises(ReviewGateError): self.check()

    def test_prior_receipt_cannot_be_removed(self):
        self.old = ledger([receipt("events", DAY0)])
        with self.assertRaises(ReviewGateError): self.check()

    def test_source_catalog_change_requires_receipt(self):
        self.after["sources"].append({"id": "extra", "url": "https://www.callofduty.com/news", "class": "Official"})
        with self.assertRaises(ReviewGateError): self.check()

    def test_source_catalog_with_receipt_passes(self):
        self.after["sources"].append({"id": "extra", "url": "https://www.callofduty.com/news", "class": "Official"})
        self.after["reviewed"] = DAY1
        self.new["reviews"].append(receipt("sources", src="extra"))
        self.assertEqual(self.check(), ["sources"])

    def test_two_changes_with_two_receipts_pass(self):
        self.change()
        self.after["events"].append({"title": "Upcoming event", "source": "act"})
        self.after["reviewedSections"]["events"] = DAY1
        self.new["reviews"].append(receipt("events"))
        self.assertEqual(self.check(), ["events", "patches"])

    def test_unrelated_receipts_are_not_allowed(self):
        self.new["reviews"].append(receipt("events"))
        with self.assertRaises(ReviewGateError): self.check()

    def test_snapshot_date_must_cover_review(self):
        self.change()
        self.after["reviewed"] = DAY0
        with self.assertRaises(ReviewGateError): self.check()


if __name__ == "__main__":
    unittest.main()
