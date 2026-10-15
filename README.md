# Tencerem — Phase 5

Turkish-first meal decisions with optional AI-assisted intent and catalog choice, persistent preferences, **Mutfağım** and deterministic ingredient baskets. Ne yiyeceğini düşünme. Tencerem düşünsün. Now includes deterministic package purchasing and comparison using explicitly labeled demo prices. No generated recipes, real retailer integration, live prices or payments.

Accounts require **PostgreSQL + Alembic migrations + AUTH_SECRET**. No usable PostgreSQL/Docker was found here, so database/account verification used explicitly isolated SQLite test files and PostgreSQL offline migration SQL. SQLite is not a production fallback. See [AUTH_AND_USERS](docs/AUTH_AND_USERS.md), [PERSONALIZATION](docs/PERSONALIZATION.md), [PANTRY](docs/PANTRY.md) and [VERIFICATION](docs/VERIFICATION.md).

## Layout
frontend/ contains Next.js App Router; backend/app/ contains API, configuration, DB readiness and schemas; backend/tests/ contains API tests; docs/ contains product brief, architecture, decisions, roadmap and verification results. Recipe schemas, a validated JSON catalog repository, and normalization/scaling/recommendation services now implement the domain. Phase 3 adds SQLAlchemy user/session/preferences/pantry models and initial Alembic migration.

## Standard setup (PowerShell)
Install Python 3.12, Node 24 LTS, pnpm and Git if they are not on PATH. Docker Desktop is optional, only for PostgreSQL. Never replace an existing runtime installation without checking it.

```powershell
cd G:\tencerem\app
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd G:\tencerem\app\frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open http://localhost:3000. API docs: http://127.0.0.1:8000/docs. Stop either process with Ctrl+C. To use another backend address, set BACKEND_URL in frontend/.env.local (server-only); root .env is read by the backend, not automatically by Next.

## Existing Codex bundled runtimes on this machine
The standard python/node/git commands are unavailable on PATH here. These session-discovered paths also work without installing system runtimes:

```powershell
$runtime = 'C:\Users\myavu\.cache\codex-runtimes\codex-primary-runtime\dependencies'
$env:Path = "$runtime\node\bin;$runtime\native\git\cmd;$runtime\bin\fallback;$env:Path"
cd G:\tencerem\app\backend
# Already-created project environment:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# For a new environment, if bundled ensurepip fails:
# & "$runtime\python\python.exe" -m venv --without-pip .venv
# & "$runtime\python\python.exe" -m pip --python .venv\Scripts\python.exe install -r requirements.lock.txt
# & "$runtime\python\python.exe" -m pip --python .venv\Scripts\python.exe install --no-deps -e .
```

Run the PATH setup in the frontend terminal too, then use pnpm dev. Bundled runtime locations are app-managed and may change after updates.

## PostgreSQL (required for accounts; optional for anonymous trial)
Docker was not available during implementation. After installing and starting Docker Desktop:

```powershell
cd G:\tencerem\app
# Edit .env: replace POSTGRES_PASSWORD placeholder with a local-only password.
docker compose up -d db
docker compose ps
# Uncomment DATABASE_URL in .env and use the same credentials.
# URL-encode special characters in the URL password; restart the backend.
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
docker compose down
```

The named volume survives shutdown. Changing POSTGRES_PASSWORD after initialization does not change the existing DB role password; manage that explicitly. Run Alembic upgrade head after configuring the connection; application startup never creates tables. Readiness returns 503/not_configured without DATABASE_URL, 503/unavailable on connection failure, and 200/connected only after SELECT 1. Preference submission remains available without a DB.

## Checks
```powershell
cd G:\tencerem\app\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
cd ..\frontend
pnpm lint
pnpm typecheck
pnpm build
# Optional production server, after successful build:
pnpm start
```

See docs/VERIFICATION.md for observed outcomes and limitations. Dependency download requires registry access. Lockfiles capture installed dependency versions; review updates regularly.

## Phase 0 API contract (preserved)
POST /api/v1/meal-preferences accepts craving (3–240 trimmed characters), servings (integer 1–12), max_budget_try (positive decimal, at most 100000 with at most two decimal places), max_prep_minutes (integer 5–240), dietary_preference (none, vegetarian, vegan, gluten_free). Unknown fields are rejected. Successful responses contain mode=development, message and validated preferences. Money is serialized as a decimal string. Validation errors use error.code, error.message and error.fields; server errors never reveal driver messages or credentials.

## Limitations and next milestone
Local application with curated recipes, persistent accounts/preferences/pantry and conservative allergen exclusions. No certified allergy safety, real retailer products/live prices, payments or public deployment. Demo products/prices are development fixtures only. Frontend budget is total basket budget, not per serving. Dietary options are preferences, not medical guarantees. Add production ingress limits/rate limiting and deployment hardening before public exposure. Initial migration is 0001_accounts.

Phase 2 ingredient aggregation and basket preview are complete. Phase 3 accounts/pantry/personalization are complete at the documented test level. Phase 4 adds optional AI-assisted decisions. Phase 5 adds a static demo market catalog, deterministic package selection and comparison; real PostgreSQL, provider evaluation and deployment/privacy hardening remain open. No real retailer or live-price integration is included. See docs/ROADMAP.md.


## Phase 1 recipe API and behavior
- `GET /api/v1/recipes`: full validated catalog, at base servings.
- `GET /api/v1/recipes/{slug}?servings=6`: recipe plus scaled ingredients (defaults to base servings); unknown slug returns actionable 404.
- `POST /api/v1/recipes/recommend`: deterministic matching; returns requested servings, recipes, scaled ingredients, available/missing lists, reasons, provenance, normalized/recognized/unknown pantry entries, and explicit budget limitations.

```powershell
$preferences = @{craving='tavuk'; servings=2; max_prep_minutes=30; dietary_preference='none'; pantry='pirinç, yoğurt'} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/recipes/recommend -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($preferences))
Invoke-RestMethod http://127.0.0.1:8000/api/v1/recipes/tavuklu-pilav?servings=6
```

Recommendation craving is 2–240 trimmed characters (supports `et`); servings 1–12; `max_prep_minutes` means **total preparation + cooking time**, 5–240; diet is none/vegetarian/vegan/gluten_free. `pantry` is an optional comma-separated string up to 1000 characters. Optional `limit` is 1–10 (default 5). `max_budget_try` is optional here, validated when supplied, but never used for scoring or filtering. Phase 0's original 3-character craving and required-budget contract is unchanged.

Recipes are development formulations, not externally sourced or professionally kitchen-tested. No nutritional numbers are claimed. Pantry presence does not imply sufficient quantity or equivalent preparation state: the `nohut` alias resolves to **haşlanmış nohut**, so check ingredient notes. Unknown pantry entries are shown instead of guessed. Optional ingredients, salt, and water remain explicit in the lists. Time estimates do not scale with servings. There are no density conversions.

See [recipe engine contract](docs/RECIPE_ENGINE.md) for scoring weights, rounding, unit labels, data integrity, limitations and Phase 2 boundaries. Browser smoke instructions and actual check outcomes are in [verification](docs/VERIFICATION.md). The existing browser-smoke entry point now runs the Phase 1 flow and includes a Phase 0 endpoint regression check.

## Git checkpoint (Phase 2 historical strategy)
Phase 0, Phase 1 and Phase 2 all began without an existing commit. No source was staged, committed, pushed or deleted. Recommend **A: one reviewed combined initial checkpoint**, because the current tree includes all three phases and no authentic prior snapshots exist in Git. Arbitrarily staging today’s files as separate phase commits would create misleading history and potentially incomplete intermediate states. Suggested message: `feat: establish Tencerem recipe and smart basket foundation`. Review ignored secrets and the entire untracked tree before staging. Separate historical commits are safe only if genuine earlier snapshots can be reconstructed and tested in a separate workspace.


## Phase 2: recipe → pantry → ingredient basket
The primary UI now presents one meal and **Başka Öner** cycles ranked alternatives. Choose **Bunu Yapacağım**, inspect the recipe, choose **Eksikleri Gör**, enter known pantry quantities (or leave them unknown), then **Sepete Hazırla**. Optional ingredients default off. The basket shows required, available, allocated and missing quantities, recipe provenance/calculations, warning states, a deterministic summary and a local checklist. Changing stock, optional policy or selected meal invalidates the previous preview. Nothing is persisted or deducted from actual stock.

- `GET /api/v1/ingredients`: canonical registry with aliases, category, preferred dimension/unit and subtraction capability.
- `POST /api/v1/baskets/preview`: one or more selected recipes/servings, quantified or presence-only pantry, optional policy. All Phase 0/1 APIs remain available.
- Safe conversions: kg→g, l→ml, identical counts. Culinary units stay separate; no density or spoon-volume guesses.
- Duplicate pantry entries in the same compatible group are rejected to prevent double counting. Unknown quantity never implies full coverage.
- A basket item is an ingredient requirement, not a retailer product. There are no prices, checkout or persistent pantry.

```powershell
$basketRequest = @{
  recipes = @(@{slug='tavuklu-pilav';servings=3}, @{slug='tavuk-sote';servings=2})
  pantry = @(@{ingredient_id='chicken_breast';quantity='0.4';unit='kg'}, @{ingredient_id='salt';quantity=$null;unit=$null;presence=$true})
  optional_policy = 'required_only'
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/baskets/preview -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($basketRequest))
```

This catalog example requires 600 g chicken, allocates 400 g from pantry, and leaves 200 g missing. Multiple recipes are supported by the API; the current UI deliberately accepts one meal at a time. See [BASKET_ENGINE.md](docs/BASKET_ENGINE.md) for the full contract and limitations and [VERIFICATION.md](docs/VERIFICATION.md) for exact executed commands and results. Startup commands above are unchanged; no dependency installation is needed for Phase 2 on this machine.


## Phase 3 setup and use
The combined Phase 0–2 checkpoint now exists as `c410b49`; Phase 3 began from a clean working tree. No commit or push was created automatically.

1. Update project dependencies using the standard backend commands above (requirements.lock.txt now includes Argon2id/email validation).
2. Configure a private root .env: DATABASE_URL must use postgresql+psycopg; generate a real AUTH_SECRET (at least 32 characters), replace all placeholders, and use explicit CORS_ORIGINS. Set COOKIE_SECURE=false only for local HTTP; production requires HTTPS/Secure cookies.
3. From backend run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start frontend with pnpm dev as before. Choose Kayıt Ol, optionally save preferences, then add ingredients in Mutfağım. Home quietly uses saved constraints/defaults; today's servings/time override defaults without saving. Accept a meal and generate a basket using Mutfağım without re-entering stock. Logout revokes the current session; login restores saved records. The cookie is HttpOnly; there is no browser token storage.

New authenticated API: auth/register, auth/login, auth/logout; me; me/preferences; me/pantry (+ PATCH/DELETE item UUID); me/recipes/recommend; me/baskets/preview, all under /api/v1. Anonymous recipe/basket APIs retain their original contracts. Browser account writes require exact Origin plus X-Tencerem-CSRF:1; see AUTH_AND_USERS.md for API/client details. Missing DB/secret returns actionable account-service errors; anonymous trial still works.

For a local **isolated test demonstration only**, without installing PostgreSQL:

```powershell
cd G:\tencerem\app
.\scripts\run-account-test-api.ps1
# Second terminal, after the bundled-runtime PATH setup above:
cd frontend
$env:BACKEND_URL='http://127.0.0.1:8013'
pnpm exec next start --hostname 127.0.0.1 --port 3013
```

Build the frontend first. Open http://127.0.0.1:3013. The helper only enables SQLite in an explicit test environment, migrates backend/.test-data/phase3-browser.sqlite, and creates an ephemeral secret in process environment without printing it. Rerunning keeps test account records but rotates the test secret, invalidating old cookies. These files are ignored; never use real credentials/data in this fixture. Both processes stop with Ctrl+C. This demonstrates persistence behavior but does not verify PostgreSQL operational behavior.

Migrations: `python -m alembic downgrade base` is destructive to all Phase 3 tables; use only on disposable databases or after a deliberate backup. `upgrade head` re-applies. `upgrade head --sql` emits PostgreSQL SQL for review. Production never uses metadata.create_all.


## Real PostgreSQL verification checkpoint — not completed
A fresh verification attempt from Phase 3 commit d13965f confirmed 111 passing backend tests, compile checks, frontend lint/typecheck/build, and the anonymous browser flow **without a database**. No usable PostgreSQL/Docker instance or configured disposable connection was found; PostgreSQL migration, authentication, isolation, persistence, constraint/concurrency and authenticated-browser checks were not run. No SQLite result is being presented as PostgreSQL verification. No application or migration changes were made, and Phase 4 was not started.

See [VERIFICATION.md](docs/VERIFICATION.md) for the exact attempted checks and remaining scope. [AUTH_AND_USERS.md](docs/AUTH_AND_USERS.md) now contains a conditional, not-yet-executed disposable Compose setup/identity/schema/migration runbook. To resume, make a clearly identified disposable PostgreSQL environment available; this checkpoint does not install PostgreSQL/Docker or provision paid infrastructure.


## Phase 4 — natural-language decisions
The home now accepts requests such as “Evde tavuk var, hızlı ve proteinli bir şey istiyorum”, shows one curated meal, and supports Başka Öner/refinements and the existing recipe → pantry → basket flow. The original structured form and deterministic APIs remain available. Today's intent is never saved to preferences.

Optional server-only root .env settings: AI_ENABLED=false (default), AI_API_KEY (private placeholder in example), AI_MODEL (explicitly selected Structured Outputs-compatible model), AI_TIMEOUT_SECONDS=6. Without enabled/key/model the app starts and uses a clearly labeled limited Turkish rule interpreter plus deterministic ranking. No AI key is required. Never commit your key or expose it through NEXT_PUBLIC_. See [AI_DECISION_ENGINE](docs/AI_DECISION_ENGINE.md) for the provider protocol, strict schemas, safety pipeline, failure behavior, cost/privacy limits and API examples. No live provider was tested.

New read-only decision POSTs: /api/v1/assistant/recommend (anonymous) and /api/v1/me/assistant/recommend (current session). Both require an allowed Origin and X-Tencerem-CSRF:1. All quantities/safety/authorization remain deterministic. The default-off provider does not generate recipes or prices. Account persistence still requires PostgreSQL; its real runtime verification remains blocked, and isolated SQLite checks do not replace it.

```powershell
cd G:\tencerem\app\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests migrations
.\.venv\Scripts\python.exe ..\scripts\assistant-smoke.py
```

Startup/shutdown commands above remain valid; no system installation or database migration was added for Phase 4. Product branding is Tencerem. The current repository directory is `G:\tencerem\app`; setup commands use this location.

## Phase 5 — deterministic demo market estimates
After Sepete Hazırla, choose **Marketleri Karşılaştır**. Two internal sources (Tencerem Market A/B · Demo) offer 65 authored product snapshots. Code chooses minimum-cost package combinations from actual missing quantities after pantry allocation/consolidation, shows surplus, and compares complete baskets before partial ones. **Demo fiyatlar — canlı fiyat değildir.** No retailer website, API, checkout or live price is involved. No key, database migration or new dependency is required for anonymous pricing.

API: GET /api/v1/markets, GET /api/v1/markets/{retailer_id}/products, POST /api/v1/baskets/price and /compare; authenticated /api/v1/me/baskets/price and /compare use Mutfağım through the existing owner-scoped basket flow. Existing preview APIs remain unchanged. Spoon/cup needs cannot be bought from gram/ml packages by guessed conversion; these remain explicitly incomplete unless pantry covers them. Partial subtotals are not full basket prices. See [MARKET_PRICING_ENGINE](docs/MARKET_PRICING_ENGINE.md) for schemas, exact optimization limits, demo provenance and examples.

Startup remains the commands above; stop with Ctrl+C. Pricing/comparison HTTP smoke (against a running API):

```powershell
cd G:\tencerem\app
$env:TEST_BACKEND_URL='http://127.0.0.1:8000'
node scripts/pricing-smoke.cjs
```

The folder move required rebuilding ignored frontend dependency links using `pnpm install --frozen-lockfile --offline` from the local cache. Dependency versions and lockfile were preserved. If you encounter stale local links after moving a checkout, restore with the unchanged lockfile rather than changing global runtime configuration. Real PostgreSQL and live AI remain unverified; no Phase 6 work has begun.
