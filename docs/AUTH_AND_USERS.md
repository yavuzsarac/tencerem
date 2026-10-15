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
cd G:\tencerem\app\backend
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


## PostgreSQL verification checkpoint — environment unavailable (2026-10-15)
The Phase 3 commit now exists as d13965f on feature/phase-3-personalization. A fresh attempt found no usable PostgreSQL/Docker command, service, process, standard installation, listener on 5432, Docker engine pipe, project .env configuration or database connection variables in Process/User/Machine scopes. No database target was selected and no PostgreSQL migration, downgrade or account write was attempted. Current 111-test success still means isolated SQLite behavior plus offline PostgreSQL SQL compilation, **not real PostgreSQL runtime verification**. See VERIFICATION.md for results.

### Future local disposable PostgreSQL commands (not executed here)
Use this only when Docker is already installed and usable. It uses the repository's existing Compose file with a fresh project/volume, explicit disposable database and generated process-only secrets. Do not reuse an unknown database, change an existing server, print environment secrets, or run docker compose config (which can display credentials). If 5432 is occupied, do not stop the owner; use a separately reviewed disposable configuration instead.

```powershell
cd G:\tencerem\app
Get-Command docker -ErrorAction Stop | Out-Null
if (Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue) { throw '5432 is occupied; do not modify the existing service.' }
$verificationProject='tencerem-pg-verify-'+([guid]::NewGuid().ToString('N').Substring(0,8))
$env:POSTGRES_USER='tencerem_verify'
$env:POSTGRES_DB='tencerem_phase3_verify'
$env:POSTGRES_PASSWORD=[Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:AUTH_SECRET=[Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:DATABASE_URL="postgresql+psycopg://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@127.0.0.1:5432/$($env:POSTGRES_DB)"
$env:ENVIRONMENT='test'
$env:ALLOW_TEST_SQLITE='false'
$env:COOKIE_SECURE='false'
$env:CORS_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]'
docker compose -p $verificationProject up -d db
# Wait until pg_isready succeeds; do not continue on a nonzero exit code.
docker compose -p $verificationProject exec -T db pg_isready -U $env:POSTGRES_USER -d $env:POSTGRES_DB
# Inspect safe identity/version information, never a connection URL/password.
docker compose -p $verificationProject exec -T db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c 'SELECT current_database(), current_user, version();'
# Must be zero before a clean-upgrade verification; otherwise stop and investigate.
docker compose -p $verificationProject exec -T db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT count(*) AS public_tables FROM pg_tables WHERE schemaname='public';"
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Check every command result before continuing. PostgreSQL 17-alpine is the configured image, not an observed server version in this checkpoint. Record actual version, database and unique Compose project/volume before any destructive test. Inspect the resulting schema through the same Compose project from the repository root:

```powershell
docker compose -p $verificationProject exec -T db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c '\dt public.*'
docker compose -p $verificationProject exec -T db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname;"
docker compose -p $verificationProject exec -T db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT conrelid::regclass,conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE connamespace='public'::regnamespace ORDER BY conrelid::regclass::text,conname;"
```

Expected declarations (still not runtime-inspected here): users, user_preferences, auth_sessions, pantry_entries plus alembic_version; normalized-email uniqueness; per-user ingredient uniqueness; user FKs with ON DELETE CASCADE; session owner/expiry and pantry owner indexes; positive servings and paired nullable quantity/unit checks. Verify actual timestamp/NUMERIC behavior and ORM updates using real writes, not just this declaration list.

Before downgrade, manually confirm this is the fresh disposable instance/project above, current_database() is tencerem_phase3_verify, and no valuable account/pantry data exists. In the same backend terminal with the same process environment, a non-writing identity guard can precede the destructive commands:

```powershell
.\.venv\Scripts\python.exe -c "import os; from sqlalchemy import create_engine,text; from sqlalchemy.engine import make_url; u=make_url(os.environ['DATABASE_URL']); assert u.get_backend_name()=='postgresql' and u.host in ('127.0.0.1','localhost') and u.database=='tencerem_phase3_verify'; e=create_engine(u); c=e.connect(); assert c.scalar(text('SELECT current_database()'))=='tencerem_phase3_verify'; c.close(); e.dispose()"
if ($LASTEXITCODE -ne 0) { throw 'Disposable database identity check failed; do not downgrade.' }
# Only after the identity/provenance/manual-data checks above:
.\.venv\Scripts\python.exe -m alembic downgrade base
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The guard is an extra identity check, not proof of disposability; the fresh isolated project and operator confirmation remain necessary. Do not use the existing SQLite test helper for PostgreSQL verification, and do not change tests/test_accounts.py to target an arbitrary developer database: its fixture intentionally uses SQLite. Real PostgreSQL checks must explicitly exercise the application with the verified PostgreSQL target, two synthetic users, constraints/rollback, persistence, and saved-basket/personalization scenarios.

With the app and frontend running on that PostgreSQL target, account-smoke.cjs can exercise the browser flow using FRONTEND_URL and TEST_BACKEND_URL overrides; browser-smoke.cjs covers anonymous regressions. Set SCREENSHOT_PREFIX to an ignored artifact path to preserve historical screenshots. At the end, stop only the dedicated app processes and, from the repository root, run `docker compose -p $verificationProject down`. This preserves its volume; no deletion command is necessary. For an already existing native/remote PostgreSQL instance, have its owner provision and identify a disposable test database; none of these commands authorize operating on unknown databases.
