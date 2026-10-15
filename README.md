# Tencerem — Phase 2

Turkish-first meal preferences matched deterministically against 24 locally authored recipes. Includes one primary recommendation, serving scaling, quantity-aware pantry comparison, and a deterministic ingredient basket preview. No AI provider, price feed, database, or new dependency is required for this slice. The Phase 0 development receipt endpoint remains available.

## Layout
frontend/ contains Next.js App Router; backend/app/ contains API, configuration, DB readiness and schemas; backend/tests/ contains API tests; docs/ contains product brief, architecture, decisions, roadmap and verification results. Recipe schemas, a validated JSON catalog repository, and normalization/scaling/recommendation services now implement the domain. Database models and migrations remain deferred until persistence is needed.

## Standard setup (PowerShell)
Install Python 3.12, Node 24 LTS, pnpm and Git if they are not on PATH. Docker Desktop is optional, only for PostgreSQL. Never replace an existing runtime installation without checking it.

```powershell
cd G:\tencerem\mealpilot-ai
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd G:\tencerem\mealpilot-ai\frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open http://localhost:3000. API docs: http://127.0.0.1:8000/docs. Stop either process with Ctrl+C. To use another backend address, set BACKEND_URL in frontend/.env.local (server-only); root .env is read by the backend, not automatically by Next.

## Existing Codex bundled runtimes on this machine
The standard python/node/git commands are unavailable on PATH here. These session-discovered paths also work without installing system runtimes:

```powershell
$runtime = 'C:\Users\myavu\.cache\codex-runtimes\codex-primary-runtime\dependencies'
$env:Path = "$runtime\node\bin;$runtime\native\git\cmd;$runtime\bin\fallback;$env:Path"
cd G:\tencerem\mealpilot-ai\backend
# Already-created project environment:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# For a new environment, if bundled ensurepip fails:
# & "$runtime\python\python.exe" -m venv --without-pip .venv
# & "$runtime\python\python.exe" -m pip --python .venv\Scripts\python.exe install -r requirements.lock.txt
# & "$runtime\python\python.exe" -m pip --python .venv\Scripts\python.exe install --no-deps -e .
```

Run the PATH setup in the frontend terminal too, then use pnpm dev. Bundled runtime locations are app-managed and may change after updates.

## Optional PostgreSQL
Docker was not available during implementation. After installing and starting Docker Desktop:

```powershell
cd G:\tencerem\mealpilot-ai
# Edit .env: replace POSTGRES_PASSWORD placeholder with a local-only password.
docker compose up -d db
docker compose ps
# Uncomment DATABASE_URL in .env and use the same credentials.
# URL-encode special characters in the URL password; restart the backend.
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
docker compose down
```

The named volume survives shutdown. Changing POSTGRES_PASSWORD after initialization does not change the existing DB role password; manage that explicitly. No schema is created yet. Readiness returns 503/not_configured without DATABASE_URL, 503/unavailable on connection failure, and 200/connected only after SELECT 1. Preference submission remains available without a DB.

## Checks
```powershell
cd G:\tencerem\mealpilot-ai\backend
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
Local development application with curated recipes. No storage, accounts, allergy verification, grocery products, live prices, payments or public deployment. Frontend budget is total basket budget, not per serving. Dietary options are preferences, not medical guarantees. Add production ingress limits/rate limiting and deployment hardening before public exposure. No Alembic migrations exist until the first table is designed.

Phase 2 ingredient aggregation and basket preview are complete. Next recommended: ingredient preparation-state verification and quantity-entry/usability refinement (Phase 3, not started). No retailer or price integration is included. See docs/ROADMAP.md.


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

## Git checkpoint
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
