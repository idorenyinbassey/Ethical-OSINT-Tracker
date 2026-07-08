# Ethical-OSINT-Tracker: Submitted Issues Summary

**Generated:** 2026-07-08

## Executive Summary

The Ethical-OSINT-Tracker repository has **15 open issues**, all submitted on 2026-06-14 by security auditor `tg12`. These issues span critical security vulnerabilities, privacy concerns, architectural weaknesses, and testing gaps. All issues are currently **OPEN** and require resolution.

### Statistics

| Metric | Count |
|--------|-------|
| **Total Issues** | 15 |
| **Open Issues** | 15 |
| **Closed Issues** | 0 |
| **Critical Severity (P0)** | 2 |
| **High Severity (P1)** | 6 |
| **Medium Severity (P2)** | 6 |
| **Low Severity (P3)** | 1 |

### Severity Breakdown

| Severity | Count | Priority | Issues |
|----------|-------|----------|--------|
| **CRITICAL** | 2 | P0 | #3, #4 |
| **HIGH** | 6 | P1 | #5, #6, #7, #8, #9, #11 |
| **MEDIUM** | 6 | P2 | #10, #12, #13, #14, #15, #16 |
| **LOW** | 1 | P3 | #17 |

---

## Critical Issues (P0)

### Issue #3: Hardcoded admin credentials (admin/changeme) shipped by default startup and CI pipeline

**State:** OPEN | **Severity:** CRITICAL | **Priority:** P0

**URL:** [#3](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/3)

**Description:** The CI workflow and startup script create or reset the admin account to hardcoded credentials `admin` / `changeme`. This password is printed to stdout and there is no requirement to change it before the application accepts logins.

**Key Concerns:**
- Any deployment following documented path ships with known admin password
- Credentials are hardcoded in `reset_admin.py`
- No forced password-change flow exists
- Affects both CI pipeline and `start.sh`

**Evidence Files:**
- `.github/workflows/ci.yml` - runs `reset_admin.py` in test setup
- `reset_admin.py` - hardcodes password
- `start.sh` - calls `reset_admin.py` on first run

---

### Issue #4: Flask debug server (debug=True, host=0.0.0.0) enabled by default, enabling unauthenticated RCE via Werkzeug debugger

**State:** OPEN | **Severity:** CRITICAL | **Priority:** P0

**URL:** [#4](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/4)

**Description:** The Flask development server is launched in debug mode by default bound to all interfaces (`0.0.0.0`), exposing the Werkzeug interactive debugger to the network. This enables unauthenticated Remote Code Execution on any unhandled exception.

**Key Concerns:**
- `debug=True` is hardcoded in `run.py`
- Binds to `0.0.0.0` (all interfaces) by default
- Default `FLASK_ENV` is `development`, not `production`
- Werkzeug debugger PIN exposure on unhandled exceptions

**Evidence Files:**
- `run.py` - contains `app.run(debug=True, host="0.0.0.0", port=3000)`
- `start.sh` - defaults to using `run.py` instead of gunicorn

---

## High Severity Issues (P1)

### Issue #5: API key encryption is a documented no-op: encrypt_api_key/decrypt_api_key are passthroughs, all keys stored in plaintext

**State:** OPEN | **Severity:** HIGH | **Priority:** P1

**URL:** [#5](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/5)

**Description:** The `crypto.py` module's encryption functions are passthroughs that return input unchanged. All third-party API keys (Shodan, VirusTotal, HIBP, Hunter.io, NumVerify, Google Cloud Vision, IPInfo) are stored in plaintext in the database.

**Key Concerns:**
- API keys exposed if database is compromised
- False sense of security from function names
- Committed `.api_keys_key` file is useless but misleading
- No encryption of sensitive credentials

**Evidence Files:**
- `app/utils/crypto.py` - passthrough implementations
- `app/repositories/api_config_repository.py` - calls fake encryption
- `.api_keys_key` - leftover from abandoned implementation

---

### Issue #6: Open registration with no approval gate and no login brute-force protection enables billing abuse and credential stuffing

**State:** OPEN | **Severity:** HIGH | **Priority:** P1

**URL:** [#6](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/6)

**Description:** The `/register` route is publicly accessible with no invitation, approval, rate limiting, or CAPTCHA. Additionally, the `/login` route has no brute-force protection.

**Key Concerns:**
- Enables billing abuse via registration of multiple accounts
- No rate limiting on registration or login
- Allows unlimited login attempts
- Existing `rate_limiter.py` utility is never used
- Violates "ethical" framing with unrestricted access to paid APIs

**Evidence Files:**
- `app/routes/auth.py` - `/register` with no guards
- `app/routes/auth.py` - `/login` with no rate limiting
- `app/utils/rate_limiter.py` - implemented but unused

---

### Issue #7: IDOR: all authenticated users can read, edit, delete, and export every other user's cases and investigations

**State:** OPEN | **Severity:** HIGH | **Priority:** P1

**URL:** [#7](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/7)

**Description:** Cross-user access vulnerability - all authenticated users can view, edit, delete, and export cases and investigations belonging to other users. Partially broken ownership guard can be bypassed when `owner_user_id` is NULL.

**Key Concerns:**
- `list_cases()` returns all cases globally with no user filter
- Ownership guard checks `if owner_user_id and ...` which skips when NULL
- Dashboard shows all users' investigations
- Users can export other users' sensitive investigation data (PII queries)
- Affects both cases and investigations

**Evidence Files:**
- `app/repositories/case_repository.py` - unfiltered `list_cases()`
- `app/routes/cases.py` - incomplete ownership checks
- `scripts/e2e_dashboard_check.py` - creates cases with `owner_user_id=None`
- `app/repositories/investigation_repository.py` - unfiltered `list_recent()`

---

### Issue #8: Any authenticated user can overwrite shared API keys and redirect API base_url to attacker-controlled hosts (SSRF)

**State:** OPEN | **Severity:** HIGH | **Priority:** P1

**URL:** [#8](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/8)

**Description:** The `/settings/save` endpoint has no admin-only guard. Any authenticated user can modify shared API keys and redirect API endpoints to attacker-controlled hosts via unsanitized `base_url` parameter.

**Key Concerns:**
- No role-based access control exists
- `User` model has no admin/role field
- `base_url` accepted without validation
- Enables SSRF attacks via unvalidated base URLs
- Any user can disable services for all other users
- Allows key substitution/destruction

**Evidence Files:**
- `app/routes/settings.py` - `/settings/save` with only `@login_required` check
- `app/models/user.py` - no `is_admin` or role field
- No validation on `base_url` parameter

---

### Issue #9: Real user photos committed to public repository under uploaded_files/ with potential GPS EXIF exposure

**State:** OPEN | **Severity:** HIGH | **Priority:** P1

**URL:** [#9](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/9)

**Description:** Three real user photos containing potentially identifying information (timestamps, possible GPS EXIF data) are committed to the public repository and are permanently accessible in git history.

**Key Concerns:**
- Privacy violation - real photos exposed publicly
- Potential GPS EXIF data leakage
- Permanent exposure in git history
- Missing `.gitignore` entry for `uploaded_files/`
- No test fixture strategy (using real images instead of synthetic)

**Evidence Files:**
- `uploaded_files/IMG20251126163613.jpg` (1,060,584 bytes)
- `uploaded_files/Photo from 2025-11-26 15-47-55.266985.jpeg` (118,956 bytes)
- `uploaded_files/Screenshot From 2025-10-05 01-13-07.png` (55,993 bytes)
- `.gitignore` - missing `uploaded_files/` entry

---

### Issue #11: Legacy /investigate/image POST route saves uploads with original filename (no UUID) and never deletes the file

**State:** OPEN | **Severity:** HIGH | **Priority:** P1

**URL:** [#11](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/11)

**Description:** The legacy image upload route uses unsanitized original filenames (no UUID) and never deletes uploaded files after analysis, leaving sensitive forensic evidence on disk.

**Key Concerns:**
- Filename collision - second upload with same name overwrites first
- No cleanup of analyzed files - persistent sensitive data
- Race conditions possible during file analysis
- Disk exhaustion vector - unbounded growth
- GPS coordinates and EXIF metadata retained indefinitely

**Evidence Files:**
- `app/routes/investigation.py` - legacy `/investigate/image` POST handler
- Missing `finally: filepath.unlink()` cleanup
- Uses `secure_filename()` directly without UUID generation

---

## Medium Severity Issues (P2)

### Issue #10: Unbounded global in-memory cache with no eviction enables memory exhaustion and leaks results across users

**State:** OPEN | **Severity:** MEDIUM | **Priority:** P2

**URL:** [#10](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/10)

**Description:** The in-memory cache is a process-global dictionary with no maximum size bound, no LRU eviction, and no per-user isolation. One user's query results are returned to other users within the TTL window.

**Key Concerns:**
- Cross-user data leakage via shared cache
- No maximum cache size - unbounded growth
- Denial-of-service via memory exhaustion
- No per-user namespace in cache keys
- VirusTotal results cached for 6 hours

**Evidence Files:**
- `app/services/cache.py` - `_CACHE` global dict with no bounds
- Cache decorator with no LRU eviction
- TTLs up to 21,600 seconds (6 hours)

---

### Issue #12: Social username search calls str.format() on user input and performs no character validation before URL construction

**State:** OPEN | **Severity:** MEDIUM | **Priority:** P2

**URL:** [#12](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/12)

**Description:** The `/investigate/social` endpoint passes unsanitized user input to `str.format()` and constructs URLs without character validation, enabling format string information disclosure and URL manipulation.

**Key Concerns:**
- `str.format()` called on user-supplied input in fallback branch
- No character validation on usernames
- SSRF risk via unsanitized URL construction
- HTTP header injection possible
- Format string attribute traversal (e.g., `{username.__class__}`)

**Evidence Files:**
- `app/services/social_client.py` - `_check_site()` with unsafe `str.format()`
- `/investigate/social` route with no input validation

---

### Issue #13: NumVerify API key transmitted in plaintext over HTTP as a URL query parameter

**State:** OPEN | **Severity:** MEDIUM | **Priority:** P2

**URL:** [#13](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/13)

**Description:** The NumVerify API client uses plaintext HTTP by default and sends API key as URL query parameter, exposing it to network observers and logging servers.

**Key Concerns:**
- Default base URL uses `http://` not `https://`
- API key in query parameters visible in transit
- Logged on API provider's servers
- Vulnerable to network sniffing and MITM
- Vulnerable to Referer header leakage

**Evidence Files:**
- `app/services/numverify_client.py` - default base URL is `http://apilayer.net/api`
- API key passed as URL query parameter
- `app/services/ip_client.py` - also uses HTTP

---

### Issue #14: Near-zero test coverage: one test file covers only config CRUD; all routes, security properties, and services are untested

**State:** OPEN | **Severity:** MEDIUM | **Priority:** P2

**URL:** [#14](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/14)

**Description:** The application has only one test file covering repository CRUD operations. All routes, security properties, services, and core features are completely untested.

**Key Concerns:**
- No authentication tests
- No IDOR protection tests
- No file upload cleanup tests
- No social input validation tests
- No rate limiting tests
- False green CI signal
- Prevents regression detection on security fixes

**Evidence Files:**
- `tests/test_settings_repository.py` - only test file
- Missing: `tests/test_auth.py`, `tests/test_cases_idor.py`, `tests/test_file_forensics.py`, etc.
- CI passes with zero meaningful test coverage

---

### Issue #15: PII (email, phone) stored indefinitely in plaintext; hash_if_sensitive() exists but is dead code never called

**State:** OPEN | **Severity:** MEDIUM | **Priority:** P2

**URL:** [#15](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/15)

**Description:** Investigation queries containing PII (email, phone numbers) are stored indefinitely in plaintext. A `hash_if_sensitive()` utility exists but is never called, creating false confidence.

**Key Concerns:**
- Email addresses and phone numbers stored permanently
- Cross-user PII exposure on dashboard
- Dead code function `hash_if_sensitive()` creates false sense of security
- GDPR/CCPA compliance violations
- No data retention policy
- No per-user isolation in dashboard queries

**Evidence Files:**
- `app/utils/crypto.py` - unused `hash_if_sensitive()` function
- `app/repositories/investigation_repository.py` - raw PII stored in `create_investigation()`
- `app/routes/dashboard.py` - `list_recent()` shows all users' PII queries

---

### Issue #16: Universal bare exception swallowing across all service clients with no logging makes failures operationally invisible

**State:** OPEN | **Severity:** MEDIUM | **Priority:** P2

**URL:** [#16](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/16)

**Description:** All HTTP service clients swallow exceptions with bare `except Exception:` blocks with no logging, making failures silent and invisible to operators.

**Key Concerns:**
- No error logging - operational blindness
- Cannot distinguish "no results" from "API failed"
- Masks security events (quota exhaustion abuse)
- Some clients expose `str(exc)` to browser UI
- No distinction between error types
- Makes debugging impossible

**Evidence Files:**
- `app/services/shodan_client.py` - bare `except Exception: return None`
- `app/services/virustotal_client.py` - bare exception swallowing
- `app/services/hibp_client.py` - no exception logging
- `app/services/darkweb_client.py` - returns generic error dict
- `app/services/social_client.py` - exposes `str(exc)` to UI
- All other service clients have same pattern

---

## Low Severity Issues (P3)

### Issue #17: No HTTP security headers (CSP, X-Frame-Options, XCTO) and no SRI on externally loaded Tailwind CDN script

**State:** OPEN | **Severity:** LOW | **Priority:** P3

**URL:** [#17](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues/17)

**Description:** The application sets no HTTP security headers (CSP, X-Frame-Options, X-Content-Type-Options) and loads Tailwind CSS from CDN without Subresource Integrity (SRI) hashing.

**Key Concerns:**
- No Content-Security-Policy header
- No X-Frame-Options (clickjacking risk)
- No X-Content-Type-Options
- No Referrer-Policy
- No Permissions-Policy
- Tailwind CDN loaded without SRI hash
- CDN compromise can inject arbitrary JavaScript

**Evidence Files:**
- All templates in `app/templates/` load Tailwind from CDN without SRI
- `app/__init__.py` - no `@app.after_request` handler for security headers
- `app/config.py` - no security header configuration

---

## Issues by Category

### Security & Access Control (7 issues)
- #3 - Hardcoded admin credentials
- #4 - Debug RCE vulnerability
- #5 - Unencrypted API keys
- #6 - Open registration & brute force
- #7 - IDOR cross-user access
- #8 - API key overwrite & SSRF
- #17 - Missing security headers

### Privacy & Data Protection (4 issues)
- #9 - Real photos in public repo
- #11 - Undeleted uploaded files
- #15 - PII stored indefinitely
- #13 - API key transmission over HTTP

### Reliability & Observability (2 issues)
- #10 - Unbounded cache growth
- #16 - Silent exception swallowing

### Testing & Quality (2 issues)
- #12 - Input validation missing
- #14 - Near-zero test coverage

---

## Summary Statistics

### All Issues by State
- **Open:** 15 (100%)
- **Closed:** 0 (0%)

### Issues by Submitter
- `tg12`: 15 issues

### Submission Timeline
- All 15 issues submitted on **2026-06-14**
- Submission time range: 23:58:22 to 23:59:28 (UTC)
- Created in descending order from #17 to #3

### Risk Assessment
- **Immediate Action Required (P0):** 2 issues
  - Critical RCE and credential exposure
- **Urgent Resolution (P1):** 6 issues
  - Multiple security & privacy vulnerabilities
- **High Priority (P2):** 6 issues
  - Important reliability and quality issues
- **Moderate (P3):** 1 issue
  - Security hardening/defense-in-depth

---

## Recommended Next Steps

1. **Immediate (P0):** Fix hardcoded credentials and debug server exposure
2. **Priority (P1):** Address API key encryption, access control, and IDOR vulnerabilities
3. **Important (P2):** Implement logging, add test coverage, fix PII handling
4. **Hardening (P3):** Add security headers and SRI

---

**Report Generated:** 2026-07-08 | **Repository:** idorenyinbassey/Ethical-OSINT-Tracker
