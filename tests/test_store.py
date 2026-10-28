"""Offline tests for safe, source-attributed public MW4 Store projections."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import refresh_store as shop

DATE = "2026-10-27T14:00:00Z"


def item(key="cod:bundle:6773", name="C.O.D.E. Valor Pack", price=None):
    return {
        "id": "6773",
        "itemKey": key,
        "name": name,
        "type": "12 items",
        "price": {"amount": price, "label": "Platform store" if price is None else None, "currency": "COD Points"},
        "images": {"card": "https://cdn.source.gs/modern-warfare-4/img/bundle-6773-preview-56cc46.webp"},
        "badge": None,
        "availability": {"from": None, "until": None},
        "contents": [{"name": "Valor", "type": "Operator Skin"}],
        "sourceUrl": "https://www.callofduty.com/en/store/bundles/6773",
    }


def payload(mw4=None, other=None, stale=False):
    return {
        "data": {
            "game": "call-of-duty", "shopDate": "2026-10-27",
            "updatedAt": "2026-10-27T05:05:02Z", "stale": stale,
            "sections": [
                {"title": "Spotlight", "upcoming": False, "items": other if other is not None else [item("bo7:bundle:9", "BO7 Only")]},
                {"title": "Modern Warfare 4", "upcoming": False, "items": mw4 if mw4 is not None else [item()]},
            ],
        },
        "meta": {"attribution": {"text": "Data from itemshop.gg", "url": "https://itemshop.gg/call-of-duty"}},
    }


class StoreProjectionTests(unittest.TestCase):
    def project(self, p=None):
        return shop.transform(p if p is not None else payload(), checked_at=DATE)

    def test_only_mw4_section_and_not_bo7_or_warzone(self):
        data = self.project()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], "cod:bundle:6773")
        self.assertNotIn("BO7", json.dumps(data))

    def test_no_personal_data_or_api_key_is_published(self):
        data = self.project()
        self.assertNotIn("Authorization", json.dumps(data))
        self.assertNotIn("isg_", json.dumps(data))
        self.assertEqual(data["provider"], "itemshop.gg")
        self.assertEqual(data["status"], "synced")

    def test_null_price_is_not_invented(self):
        price = self.project()["items"][0]["price"]
        self.assertIsNone(price["amount"])
        self.assertEqual(price["label"], "Platform store")
        self.assertEqual(price["currency"], "COD Points")

    def test_numeric_cod_points_price_kept_without_usd_conversion(self):
        data = self.project(payload(mw4=[item(price=2400)]))
        self.assertEqual(data["items"][0]["price"]["amount"], 2400)
        self.assertNotIn("USD", json.dumps(data))

    def test_untrusted_image_and_official_link_rejected(self):
        x = item()
        x["images"]["card"] = "https://evil.example/track.png"
        x["sourceUrl"] = "https://evil.example/store/6773"
        one = self.project(payload(mw4=[x]))["items"][0]
        self.assertIsNone(one["image"])
        self.assertIsNone(one["officialUrl"])

    def test_valid_provider_card_and_official_link_preserved(self):
        one = self.project()["items"][0]
        self.assertTrue(one["image"].startswith("https://cdn.source.gs/"))
        self.assertTrue(one["officialUrl"].startswith("https://www.callofduty.com/"))

    def test_empty_mw4_section_is_not_filled_with_other_games(self):
        data = self.project(payload(mw4=[]))
        self.assertEqual(data["items"], [])

    def test_duplicate_keys_are_ignored(self):
        data = self.project(payload(mw4=[item(), item()]))
        self.assertEqual(len(data["items"]), 1)

    def test_limit_is_bounded(self):
        examples = [item("cod:bundle:"+str(i), "Bundle "+str(i)) for i in range(60)]
        data = self.project(payload(mw4=examples))
        self.assertEqual(len(data["items"]), shop.MAX_ITEMS)

    def test_upcoming_and_stale_are_not_hidden(self):
        p = payload(stale=True)
        p["data"]["sections"][-1]["upcoming"] = True
        data = self.project(p)
        self.assertTrue(data["stale"])
        self.assertTrue(data["items"][0]["upcoming"])

    def test_bad_game_rejected(self):
        p = payload()
        p["data"]["game"] = "black-ops-7"
        with self.assertRaises(ValueError):
            self.project(p)

    def test_root_domain_attribution_supported_per_api_docs(self):
        p = payload()
        p["meta"]["attribution"]["url"] = "https://itemshop.gg"
        data = self.project(p)
        self.assertEqual(data["attribution"]["url"], "https://itemshop.gg")

    def test_unattributed_response_rejected(self):
        p = payload()
        p["meta"]["attribution"]["url"] = "https://unrelated.example/"
        with self.assertRaises(ValueError):
            self.project(p)

    def test_invalid_shop_date_rejected(self):
        p = payload()
        p["data"]["shopDate"] = "2026-13-52"
        with self.assertRaises(ValueError):
            self.project(p)

    def test_missing_stale_flag_rejected(self):
        p = payload()
        p["data"].pop("stale")
        with self.assertRaises(ValueError):
            self.project(p)

    def test_no_free_claim_when_price_is_missing(self):
        output = self.project()
        self.assertNotIn("free", output["items"][0]["price"])

    def test_atomic_write_valid_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "input.json"
            target = base / "data/store.json"
            source.write_text(json.dumps(payload()), encoding="utf-8")
            with patch.object(sys, "argv", ["refresh_store.py", "--input", str(source), "--output", str(target), "--checked-at", DATE]):
                self.assertEqual(shop.main(), 0)
            self.assertEqual(json.loads(target.read_text())["items"][0]["id"], "cod:bundle:6773")
            self.assertFalse(target.with_suffix(".json.next").exists())

    def test_bad_fixture_does_not_overwrite_previous_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "bad.json"
            target = base / "data/store.json"
            target.parent.mkdir()
            target.write_text("LAST GOOD DATA", encoding="utf-8")
            source.write_text(json.dumps({"data": {"game": "bogus"}}), encoding="utf-8")
            with patch.object(sys, "argv", ["refresh_store.py", "--input", str(source), "--output", str(target), "--checked-at", DATE]):
                with self.assertRaises(ValueError):
                    shop.main()
            self.assertEqual(target.read_text(), "LAST GOOD DATA")

    def test_only_expected_public_schema_fields(self):
        d = self.project()
        self.assertEqual(
            set(d), {"schema", "provider", "game", "status", "shopDate",
                      "updatedAt", "checkedAt", "stale", "attribution", "note", "items"}
        )
        self.assertEqual(d["attribution"]["text"], "Data from itemshop.gg")


if __name__ == "__main__":
    unittest.main()
