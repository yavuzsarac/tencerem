# Accounts, sessions and persistence — Phase 3

## Architecture and data
Production persistence is PostgreSQL through SQLAlchemy 2.x + psycopg; no runtime SQLite fallback exists. An explicit `ENVIRONMENT=test` and `ALLOW_TEST_SQLITE=true` are both required to create a SQLite engine. Normal startup only constructs a lazy engine and never creates tables. Alembic revision `0001_accounts` is the reviewable initial schema.

Tables: users (UUID string ID, normalized unique email, Argon2id hash, UTC timestamps); user_preferences (one-to-one owner, diet, separate allergy list, liked/disliked canonical ingredient IDs, goals, default servings/time and update timestamp); auth_sessions (HMAC digest of opaque token, owner, expiry, creation); pantry_entries (owner, canonical ingredient, nullable paired quantity/unit, optional date, timestamps). Pantry has one row per user/ingredient and no retailer identity. Cascading user foreign keys prepare for future deletion, but deletion/export endpoints are not implemented.

Email addresses are validated without delivery/DNS checks and casefolded as an explicit case-insensitive account identity policy. Unique storage plus IntegrityError handling resolves duplicate registration, including concurrent insertion at the database boundary. Accounts are not email-verified. Passwords and hashes are never returned; public users expose only ID, email and timestamps.

## Authentication decision
Use random 256-bit opaque sessions rather than JWTs. A database lookup gives immediate logout revocation, no refresh-token machinery and no token in frontend JavaScript. Session tokens are generated with secrets.token_urlsafe(32); only HMAC-SHA256 digests keyed by AUTH_SECRET are stored. The random token is in a host-only HttpOnly, SameSite=Lax, path=/ cookie. Secure defaults true; development HTTP must explicitly set COOKIE_SECURE=false. Production rejects insecure-cookie configuration. Expiry is checked server-side in UTC (including timezone-aware DB responses), default one hour, configurable 60–86400 seconds. Login rotates the current browser token; logout deletes its DB row and expires the cookie. Other sessions are not globally logged out. Expired rows are cleaned opportunistically on login/registration.

Argon2id uses random salts, 64 MiB, three iterations, parallelism one. There was no project hashing dependency; argon2-cffi was added, plus email-validator for validated email semantics. Unknown accounts still perform dummy password verification to reduce obvious account-existence timing differences. Successful login rehashes if parameters change. Passwords are 12–128 characters, never trimmed, and never logged by app code. Validation responses omit input values.

AUTH_SECRET must be a locally generated, stable secret of at least 32 characters; placeholders are rejected. Missing DB/secret gives actionable 503 for accounts while anonymous services remain usable. Rotating AUTH_SECRET invalidates all current sessions. There is no JWT signing algorithm/key exposure, browser token storage, OAuth, email verification, password reset, MFA or account recovery.

## Browser boundary and CSRF
Next's allowlisted `/api/account/[...path]` proxy forwards only known account/registry routes, cookies, content type, Origin and the CSRF header to FastAPI. It forwards Set-Cookie responses, uses no-store, rejects oversized bodies and never exposes BACKEND_URL in browser configuration. Private backend routes also return Cache-Control:no-store. Account writes (register/login/logout/preferences/pantry) require an exact allowed Origin plus X-Tencerem-CSRF:1. JSON/custom headers and restrictive credentialed CORS block simple cross-origin form writes; SameSite is defense in depth, not the only protection. Do not add wildcard origins. Read-only authenticated recommendation/basket POSTs do not mutate state.

A process-local, bounded 30-per-minute IP limit covers registration/login as a fallback. It is not distributed abuse protection; through the BFF the backend sees the proxy IP, so this limit may be shared by clients. Public deployment needs trusted ingress rate limiting and proxy identity configuration. XSS remains a risk even with HttpOnly cookies; no security certification is claimed.

Design references: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) and [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). These inform the choices; they do not certify this implementation.

## APIs and authorization
- POST /api/v1/auth/register (201, also starts session), login (200), logout (204, current-session revocation).
- GET /api/v1/me, GET/PUT /api/v1/me/preferences.
- GET/POST /api/v1/me/pantry; PATCH/DELETE /api/v1/me/pantry/{UUID}.
- POST /api/v1/me/recipes/recommend and /api/v1/me/baskets/preview.

All me routes derive ownership solely from the validated session; body user_id is forbidden. Pantry mutations query both item ID and current owner; another user's UUID and an unknown UUID produce the same 404. Malformed IDs produce 422. No API accepts SQL fragments or interpolates query text into SQL. ORM parameters handle values. Account reads/writes, preferences and pantry isolation are tested.

## Setup and migrations (PowerShell)
Copy root .env.example only if .env does not exist; configure matching local PostgreSQL credentials and DATABASE_URL. If Docker is installed by you, existing Compose can run PostgreSQL; this phase did not install it. Set AUTH_SECRET using a password manager or a generated random value and keep it out of source/history/logs. For example, generate without printing and write only the intended setting to your private .env using your editor, or set a process variable:

```powershell
$env:AUTH_SECRET = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
# Persist the same value securely if sessions should survive process restarts.
cd G:\tencerem\mealpilot-ai\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Use COOKIE_SECURE=false only for local HTTP, and configure exact frontend origins. Root .env configures FastAPI; frontend/.env.local or process environment configures Next BACKEND_URL if different from 8000. Normal frontend command remains pnpm dev. Never run downgrade on valuable data without a backup: `python -m alembic downgrade base` drops all four Phase 3 tables. Re-upgrade: `python -m alembic upgrade head`. Offline review SQL: `python -m alembic upgrade head --sql`. Do not use metadata.create_all for production.

## Privacy and limits
Stored: email/account identifiers, password hashes, temporary session digests, self-entered preferences/allergies (potentially sensitive), pantry amounts and optional dates. Needed for login, saved defaults, exclusions and stock calculation. Not collected: name, DOB, gender, address, phone, payment or retailer credentials, location, meal-intent history. Auth rate limits use ephemeral process memory and request IP; application code does not log credential bodies or pantry contents. Infrastructure/access logs require deployment review.

Before commercial deployment: real PostgreSQL migration/concurrency testing; HTTPS, managed secrets, access controls/backups, distributed abuse protection; email ownership/recovery decisions; retention, export and account deletion; and a KVKK/privacy review. No legal-compliance badge or production security certification is claimed. Real PostgreSQL was unavailable in this environment; see VERIFICATION.md for the precise SQLite/offline SQL test boundary.
