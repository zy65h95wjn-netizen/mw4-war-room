"""H1 regressions: real urllib dispatch, mocked transport, synthetic credentials only."""
import io
import json
import sys
import tempfile
import unittest
import urllib.request
from contextlib import contextmanager, redirect_stdout
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.response import addinfourl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import refresh_store as shop
from test_store import DATE, payload

SYNTHETIC_KEY = "synthetic-h1-test-only"
REDIRECT_CODES = (301, 302, 303, 307, 308)
REDIRECT_TARGETS = (
    "https://example.invalid/redirect",
    "http://itemshop.gg/redirect",
    "http://example.invalid/redirect",
    "https://itemshop.gg/redirect",
    shop.API_URL,
    "/redirect",
    "//example.invalid/redirect",
    "https://itemshop.gg:444/redirect",
    "https://itemshop.gg@example.invalid/redirect",
    "https://itemshop.gg.example.invalid/redirect",
)


def response(code=200, *, location=None, body=None, content_type="application/json",
             url=shop.API_URL, location_header="Location"):
    headers = Message()
    if content_type is not None:
        headers["Content-Type"] = content_type
    if location is not None:
        headers[location_header] = location
    result = addinfourl(io.BytesIO(body if body is not None else json.dumps(payload()).encode()),
                       headers, url, code)
    result.msg = "Synthetic response"
    return result


@contextmanager
def transport(*replies):
    """Keep the opener/redirect chain real; replace only the HTTP transport boundary."""
    requests = []
    pending = iter(replies)

    def send(_connection, req, **_kwargs):
        requests.append({"url": req.full_url, "headers": dict(req.header_items()),
                         "timeout": req.timeout, "method": req.get_method()})
        try:
            reply = next(pending)
        except StopIteration:
            raise AssertionError("Unexpected extra HTTP request") from None
        if isinstance(reply, Exception):
            raise reply
        return reply

    with patch.object(urllib.request.AbstractHTTPHandler, "do_open", side_effect=send), \
            patch.object(urllib.request, "getproxies", return_value={}), \
            patch.object(urllib.request, "_opener", None), \
            patch("socket.create_connection", side_effect=AssertionError("Real network forbidden")):
        try:
            yield requests
        finally:
            for reply in replies:
                if hasattr(reply, "close"):
                    reply.close()


class StoreHTTPTests(unittest.TestCase):
    def assert_first_request_only(self, requests):
        self.assertEqual(len(requests), 1, "Credentials must never be sent on a second request")
        self.assertEqual(requests[0]["url"], shop.API_URL)
        self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer " + SYNTHETIC_KEY)

    def test_direct_json_response_preserves_request_contract(self):
        with transport(response()) as requests:
            self.assertEqual(shop.fetch_live(SYNTHETIC_KEY), payload())
        self.assert_first_request_only(requests)
        self.assertEqual(requests[0]["method"], "GET")
        self.assertEqual(requests[0]["timeout"], 20)
        self.assertEqual(requests[0]["headers"]["Accept"], "application/json")
        self.assertEqual(requests[0]["headers"]["User-agent"],
                         "MW4WarRoom/0.4 (personal public-store companion)")

    def test_all_redirect_codes_and_destinations_stop_before_second_request(self):
        for code in REDIRECT_CODES:
            for target in REDIRECT_TARGETS:
                with self.subTest(code=code, target=target), \
                        transport(response(code, location=target), response(url=target)) as requests:
                    try:
                        with self.assertRaisesRegex(RuntimeError, f"HTTP {code}"):
                            shop.fetch_live(SYNTHETIC_KEY)
                    finally:
                        self.assert_first_request_only(requests)

    def test_missing_and_malformed_redirect_locations_fail_closed(self):
        for code in REDIRECT_CODES:
            for target in (None, "", "https://[", "file:///not-a-store", "javascript:alert(1)"):
                with self.subTest(code=code, target=target), \
                        transport(response(code, location=target), response()) as requests:
                    try:
                        with self.assertRaisesRegex(RuntimeError, f"HTTP {code}"):
                            shop.fetch_live(SYNTHETIC_KEY)
                    finally:
                        self.assert_first_request_only(requests)

    def test_legacy_uri_redirect_header_is_also_rejected(self):
        with transport(response(302, location="https://example.invalid/redirect",
                                location_header="URI"), response()) as requests:
            try:
                with self.assertRaisesRegex(RuntimeError, "HTTP 302"):
                    shop.fetch_live(SYNTHETIC_KEY)
            finally:
                self.assert_first_request_only(requests)

    def test_redirect_error_does_not_echo_location_body_or_credentials(self):
        target = "https://example.invalid/" + SYNTHETIC_KEY
        with transport(response(302, location=target, body=SYNTHETIC_KEY.encode()),
                       response(url=target)):
            with self.assertRaisesRegex(RuntimeError, "HTTP 302") as caught:
                shop.fetch_live(SYNTHETIC_KEY)
        self.assertNotIn(SYNTHETIC_KEY, str(caught.exception))
        self.assertNotIn("example.invalid", str(caught.exception))

    def test_auth_and_other_http_failures_do_not_echo_provider_response(self):
        for code in (300, 304, 401, 403, 429, 500, 503):
            with self.subTest(code=code), \
                    transport(response(code, body=SYNTHETIC_KEY.encode())) as requests:
                with self.assertRaisesRegex(RuntimeError, f"HTTP {code}") as caught:
                    shop.fetch_live(SYNTHETIC_KEY)
                self.assertNotIn(SYNTHETIC_KEY, str(caught.exception))
                self.assert_first_request_only(requests)

    def test_network_failures_are_rejected(self):
        for failure in (URLError("synthetic network failure"), URLError(TimeoutError("timed out")),
                        TimeoutError("timed out")):
            with self.subTest(kind=type(failure).__name__), transport(failure) as requests:
                with self.assertRaises((RuntimeError, OSError)):
                    shop.fetch_live(SYNTHETIC_KEY)
                self.assert_first_request_only(requests)

    def test_non_json_and_missing_content_types_are_rejected(self):
        for mime in ("text/html", None):
            with self.subTest(mime=mime), transport(response(content_type=mime)):
                with self.assertRaisesRegex(ValueError, "not JSON"):
                    shop.fetch_live(SYNTHETIC_KEY)

    def test_response_url_must_match_fixed_https_endpoint(self):
        for url in ("http://itemshop.gg/api/v1/shop/call-of-duty",
                    "https://itemshop.gg/other", "https://example.invalid/response"):
            with self.subTest(url=url), transport(response(url=url)) as requests:
                with self.assertRaisesRegex(ValueError, "Unexpected API response URL"):
                    shop.fetch_live(SYNTHETIC_KEY)
                self.assert_first_request_only(requests)

    def test_invalid_json_and_encoding_are_rejected(self):
        for body in (b"{not json", b"\xff\xfe\xff"):
            with self.subTest(body=body), transport(response(body=body)):
                with self.assertRaises(ValueError):
                    shop.fetch_live(SYNTHETIC_KEY)

    def test_oversized_response_is_rejected(self):
        with transport(response(body=b" " * (shop.MAX_JSON_BYTES + 1))):
            with self.assertRaisesRegex(ValueError, "size limit"):
                shop.fetch_live(SYNTHETIC_KEY)

    def test_invalid_keys_fail_before_any_request(self):
        for key in ("", "fake\nheader", "fake\rheader"):
            with self.subTest(key=repr(key)), transport() as requests:
                with self.assertRaisesRegex(ValueError, "not set or invalid"):
                    shop.fetch_live(key)
                self.assertEqual(requests, [])

    def run_main(self, target):
        argv = ["refresh_store.py", "--output", str(target), "--checked-at", DATE]
        with patch.object(sys, "argv", argv), \
                patch.object(shop.os, "getenv", return_value=SYNTHETIC_KEY) as getenv, \
                redirect_stdout(io.StringIO()) as output:
            try:
                return shop.main(), output.getvalue()
            finally:
                getenv.assert_called_once_with("ITEMSHOP_API_KEY", "")

    def test_failed_refreshes_preserve_existing_snapshot_bytes(self):
        failures = [
            (f"redirect-{code}", lambda code=code: response(code, location="/redirect"))
            for code in REDIRECT_CODES
        ] + [
            ("malformed-redirect", lambda: response(302, location="https://[")),
            ("unauthorized", lambda: response(401)),
            ("forbidden", lambda: response(403)),
            ("network", lambda: URLError("synthetic network failure")),
            ("timeout", lambda: TimeoutError("timed out")),
            ("read-timeout", lambda: self.read_timeout_response()),
            ("not-json", lambda: response(content_type="text/html")),
            ("invalid-json", lambda: response(body=b"{broken")),
            ("too-large", lambda: response(body=b" " * (shop.MAX_JSON_BYTES + 1))),
            ("bad-schema", lambda: response(body=b'{"data":{"game":"wrong"}}')),
            ("non-object", lambda: response(body=b'[]')),
        ]
        # The tracked public example is copied to disposable output; it is never edited.
        original = (Path(__file__).resolve().parents[1] / "data/store.json").read_bytes()
        for name, make_reply in failures:
            with self.subTest(failure=name), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "store.json"
                target.write_bytes(original)
                with transport(make_reply(), response()) as requests:
                    try:
                        with self.assertRaises((RuntimeError, ValueError, OSError)):
                            self.run_main(target)
                    finally:
                        self.assertEqual(target.read_bytes(), original)
                        self.assertFalse(target.with_name("store.json.next").exists())
                        self.assert_first_request_only(requests)

    def read_timeout_response(self):
        result = response()
        result.read = Mock(side_effect=TimeoutError("timed out"))
        return result

    def test_successful_direct_refresh_preserves_projection_and_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "store.json"
            target.write_text("previous snapshot", encoding="utf-8")
            with transport(response()) as requests:
                status, output = self.run_main(target)
            self.assertEqual(status, 0)
            actual = target.read_text(encoding="utf-8")
            self.assertEqual(json.loads(actual), shop.transform(payload(), checked_at=DATE))
            self.assertNotIn(SYNTHETIC_KEY, actual + output)
            self.assertFalse(target.with_name("store.json.next").exists())
            self.assert_first_request_only(requests)


if __name__ == "__main__":
    unittest.main()
