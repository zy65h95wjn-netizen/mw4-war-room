# H1: authenticated Store redirect repair

Scope: H1 only, for independent review. This change is not a release approval.
Base: `a6cb65815f9c8c2d291c3f80a60f1e8f8c983121` (audited v0.4.5).

## Defect and correction

`fetch_live()` used `urllib.request.urlopen()` with Authorization as a regular
request header. The default redirect handler could forward that header before
the final hostname check ran. A same-host HTTP downgrade also passed that check.
This was reproduced with synthetic credentials and mocked transport; it is not
evidence that the production credential was exposed.

The authenticated call now creates a local opener with `RejectStoreRedirects`.
Its HTTP error handlers reject 301, 302, 303, 307 and 308 before parsing Location
or constructing a redirected request. Same-host and relative redirects are also
rejected. Other non-success statuses retain urllib's failure handling. The final
response URL must equal the fixed HTTPS API URL as a secondary check. HTTP error
responses are closed, and errors report the status code without echoing response
bodies, redirect targets or credentials. Global urllib behavior is unchanged.

The direct GET endpoint, headers, 20-second timeout, size limit, JSON checks,
MW4 projection, attribution and atomic snapshot replacement are preserved.
If the provider begins legitimately redirecting this fixed endpoint, refreshes
will fail and retain the old snapshot until an endpoint change is reviewed.

## Reproduce before and after

Use a checkout of this PR. Tests require only Python's standard library. They
replace the HTTP transport boundary while running urllib's real opener, HTTP
error processor and redirect dispatch. Every request uses a synthetic key; a
socket guard forbids accidental real connections. Main-entry tests stub the
credential lookup without reading the production environment variable.

Run the added tests against the audited implementation loaded into memory
(this does not replace working files):

```sh
python -B -c "import subprocess,types,sys,unittest; code=subprocess.check_output(['git','show','a6cb65815f9c8c2d291c3f80a60f1e8f8c983121:scripts/refresh_store.py']); original=types.ModuleType('refresh_store'); exec(compile(code,'baseline/refresh_store.py','exec'),original.__dict__); sys.modules['refresh_store']=original; suite=unittest.defaultTestLoader.discover('tests',pattern='test_store_http.py'); result=unittest.TextTestRunner(verbosity=1).run(suite); sys.exit(not result.wasSuccessful())"
```

Expected: nonzero exit. The original implementation sends a second request in
the redirect cases. The assertions record that failure even when the later URL
check rejects the response. Same-origin redirects can overwrite the disposable
previous snapshot. Malformed locations can escape as URL-parsing errors.

Run against the repaired implementation:

```sh
python -B -m unittest discover -s tests -p test_store_http.py -v
python -B -m unittest discover -s tests -v
python -B scripts/validate_intel.py
node --test tests/logic.test.cjs tests/store.test.cjs tests/arsenal.test.cjs
node --check logic.js
node --check store.js
node --check app.js
node --check arsenal.js
node --check sw.js
```

The existing validation workflow discovers the new Python test file without
workflow changes. The PR's required check must be assessed at its actual head SHA.

## Recorded local evidence — October 28, 2026

Environment: Windows, Python 3.14.7, Node 24.21.0.

| Check | Result |
| --- | --- |
| Existing tests before repair | 101 Python / 41 JavaScript passed |
| New tests against audited source | 14 methods executed; 64 subtest failures and 6 errors; exit 1 |
| Complete Python suite after repair | 115 passed, including all 14 H1 methods |
| JavaScript suite after repair | 41 passed |
| Intel schema and five JavaScript syntax checks | Passed |
| Editorial gate with unchanged intel and ledger | Passed: no editorial change |

The H1 matrix covers 50 redirect status/destination pairs, 25 missing/malformed
Location cases, the legacy URI redirect header, and error-message redaction.
Additional cases cover 401/403, other HTTP errors, network/read timeouts,
non-JSON content, invalid JSON/encoding, oversized bodies, mismatched response
URLs, invalid keys, and successful direct requests. Sixteen failed-refresh
cases preserve a disposable copy of the tracked public Store snapshot byte for
byte and create no `.next` file. Successful refresh output matches the existing
projection including attribution; synthetic credentials are absent from output.

Initial baseline runs encountered Windows sandbox temporary-directory errors
(7 Python errors) and checkout CRLF conversion (22 JavaScript failures).
The Python tests passed with normal temporary-directory access. Reading `app.js`
as its exact committed LF bytes resolved the existing JavaScript harness's
literal newline marker. No test assertions or application code were weakened
to resolve these environment issues.

## Preservation and limits

- No application UI, 33-weapon roster, artwork, rankings, loadouts, events,
  Battle Pass, public Store JSON, editorial receipts or workflow files changed.
- The separate `store-feed` branch and credential isolation are unchanged.
  No production API key was retrieved, printed, rotated or used.
- Legitimate direct-request behavior is verified with mocked HTTP and the
  existing projection tests. No live authenticated provider call was made.
- Both existing browser smoke scripts stop at `ModuleNotFoundError: playwright`
  locally; their known stale assertions (M4) remain outside this H1 repair.
  No browser, Safari, VoiceOver, installed-PWA, real offline or iPhone pass is
  claimed. Existing JavaScript tests are Node tests, not physical-device tests.
- M1–M6 and L1–L2 remain for separately authorized work. No repository security
  settings, workflows, merges or deployments are part of this change.

The audited base remains the rollback reference. Before merge, production still
uses the audited implementation and H1 remains present there. Reverting the
repair after a future merge would restore the vulnerability; review that tradeoff
before any rollback. Owner review and independent retesting are required before
merging or deploying.
