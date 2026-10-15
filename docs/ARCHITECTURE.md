# Architecture — current Phase 3

Production persistence is PostgreSQL + SQLAlchemy 2.x with explicit Alembic migration 0001_accounts. Tables are users, auth_sessions, user_preferences and pantry_entries; UTC timestamps, owner FKs, unique normalized email and per-user ingredient uniqueness enforce boundaries. JSON columns hold typed preference lists without mixing today's intent into storage. Startup never creates tables. SQLite is accepted only under two explicit test flags; real PostgreSQL remains required for normal account deployment.

Account transport is Next same-origin allowlisted proxy → FastAPI account routes/dependencies → ORM session. Authentication uses random opaque HttpOnly cookies with HMAC digests/expiry in the DB, Argon2id passwords, origin/header CSRF checks, restrictive credentialed CORS and no-store private responses. No JWT/refresh infrastructure was introduced.

Services: auth owns hashes/sessions/security checks; profiles owns saved preferences and pantry overlays; personalization composes persistent hard constraints and current MealIntent around the existing ranker. Account handlers scope all owner reads/mutations by authenticated user. Saved basket endpoints call the original Phase 2 engine after loading only that user's pantry. The registry adds preparation states and explicit/incomplete allergen metadata. Public anonymous endpoints remain independent of persistent profiles and database availability.

Frontend provider loads current-user state; /kayit and /giris provide auth; /tercihlerim provides optional onboarding/profile; /mutfagim manages persisted stock. Home remains a short meal-intent flow and uses saved constraints automatically when logged in. Account BFF routes forward cookies and Set-Cookie without exposing tokens to JavaScript. Current intent is not persisted; temporary stock edits never mutate saved records.

Detailed contracts/security/privacy: AUTH_AND_USERS.md, PERSONALIZATION.md, PANTRY.md. Known verification limit: migration round trips/account/browser behavior ran on isolated SQLite; PostgreSQL SQL generation was checked but no real PostgreSQL server was available. Prior phase records below are historical where they describe missing accounts/persistence.

## Phase 0–2 architecture history

# Architecture — current Phase 2

Phase 0/1 remain intact; the records below are historical where they describe disabled baskets or multiple primary cards. New flow: ranked recommendation → one primary meal → acceptance and recipe → quantity review → Next same-origin basket proxy → FastAPI basket service → ingredient requirements with provenance. No database, new runtime dependencies or external service is needed.

- Ingredient registry: `repositories/ingredients.py`, extended `IngredientDefinition` and metadata in the existing `data/ingredients.json`. Shared exact alias resolution serves Phase 1 pantry matching and new registry clients; catalog startup validation rejects orphans/ambiguous aliases.
- Quantity service: `services/quantities.py` owns Decimal normalization for safe unit pairs and precise display. It never assumes densities or culinary volumes.
- Pantry service: `services/pantry.py` validates registry IDs/duplicate stock buckets and builds a fresh normalized inventory. Unknown quantity is explicit, not unlimited.
- Basket service: `services/baskets.py` scales selected recipes, filters optional contributions, groups canonical ingredient/unit components and allocates pantry once after consolidation. It preserves original recipe source quantities and provenance.
- API/schema layer: `schemas/baskets.py`, `api/baskets.py` expose registry GET and stateless basket preview POST. Domain input errors use the existing structured 422 envelope; handlers contain no arithmetic. App API version is 0.3.0.
- Frontend: single-recommendation `recipe-results`, quantity editor `pantry-basket`, and `basket-preview` with explanations/checklist. Shared proxy adds a bounded 64 KiB basket route, retaining existing route limits/timeouts. Stock edits invalidate previews; checkbox state is local and ephemeral.

See [BASKET_ENGINE.md](BASKET_ENGINE.md) for exact status, quantity and summary semantics. Quantity components are ingredient requirements, not supermarket SKUs; this boundary remains available for future integrations. Database readiness/security controls below are unchanged. No basket/pantry migrations, persistence, accounts or retailers were introduced.

## Phase 1 architecture record (historical)

# Architecture — current Phase 1

The Phase 0 architecture remains in place. Next.js renders the Turkish preference form, POSTs to its same-origin `/api/recipes/recommend` route, and forwards to FastAPI. The legacy same-origin `/api/meal-preferences` proxy and versioned development receipt remain available. Both proxies share a timeout/error/size-check helper. Database liveness/readiness semantics remain unchanged; recipe endpoints are stateless and need no PostgreSQL connection.

New boundaries:
- `schemas/recipes.py`: immutable domain models, controlled units, scaled/recommendation response contracts.
- `repositories/catalog.py` and `data/*.json`: locally authored recipe/ingredient catalog with eager validation and stable identities.
- `services/normalization.py`: Turkish comparison normalization and canonical pantry resolution.
- `services/scaling.py`: Decimal serving scaling, display formatting, no unit conversion.
- `services/recommendation.py`: hard time/diet filters and explainable weighted ranking.
- `api/recipes.py`: transport-only list/detail/recommend routes using the application-scoped catalog.
- `frontend/components/recipe-results.tsx`: source-labeled recipe cards, ingredient partitions, instructions and disabled future-basket CTA.

Catalog data ships as Python package data and validates at application creation; no runtime downloads, database migrations, provider calls or new dependencies are required. API version is 0.2.0. No model/repository interface hierarchy was added beyond the concrete catalog. See [recipe engine contract](RECIPE_ENGINE.md) for exact algorithms, units, rounding and limitations. Shared security/configuration controls below still apply; POST bodies remain bounded by fields and proxy checks, with public ingress limits deferred.

## Phase 0 architecture record (historical)


## Components and flow
Next.js App Router renders the Turkish UI. A client form uses native constraints and a trimmed-text check. It POSTs to the same-origin Next route, which forwards to FastAPI with an eight-second timeout. The browser has a twelve-second timeout and retryable error state. FastAPI/Pydantic owns validation and returns a typed development receipt; malformed requests return a consistent error envelope. Numeric budgets use Decimal to avoid binary floating point for future money operations.

The API has small api, core, db, and schemas packages. Models, repositories, and services will be introduced when persistent entities and business behavior exist; empty speculative layers are deliberately omitted. There is no authentication, recipe generation, or persistence.

## Health semantics
/health and /api/v1/health are process liveness. /api/v1/ready returns 200 only after a SQLAlchemy PostgreSQL SELECT 1 succeeds. Unconfigured and unreachable databases return 503 with separate database statuses. The stateless preference endpoint remains usable without DB readiness. A deployment of this stateless slice should use liveness; future persistent routes will require readiness. Probe connections are disposed and have a three-second connection timeout. No tables are auto-created.

## Data strategy
PostgreSQL 17 is the optional local database, exposed only on loopback with a named volume. SQLAlchemy 2.x supplies the real readiness query. Alembic is installed for future migrations; no migration configuration or empty revision exists because there is no schema yet. Future persisted recipe and ingredient models require reviewed migrations and backup/restore procedures.

## Configuration and security
Backend reads root .env via an absolute path derived from the module and honors process environment overrides. DATABASE_URL uses SecretStr; connection errors never reach clients. Next reads BACKEND_URL from process environment or frontend/.env.local; it defaults to loopback. Nothing secret uses NEXT_PUBLIC_. The browser calls its own origin. CORS is limited to configured origins for optional direct API development. Raw request contents and preferences are not logged by application code. Errors omit submitted values and stack traces. .env and local artifacts are ignored.

The proxy limits preference payload size after reading; this is not an ingress memory defense. Before any public deployment add ingress request-size limits, rate limits, HTTPS, observability with redaction, deployment-specific origin policy, and dependency scanning. No public production deployment is supplied. The development servers bind loopback by default.

## Integration boundaries
Later add recipe-generation services behind validated domain schemas, ingredient normalization and basket services, and authorized retailer adapters with provenance/timestamps. Keep AI secrets on the backend. No provider abstraction, queues, billing, or microservices are built now.


## PostgreSQL runtime verification attempt — environment unavailable (2026-10-15)
The architecture remains unchanged at commit d13965f. A fresh check found no usable PostgreSQL instance, Docker engine or configured disposable target. The 111 existing tests still use isolated SQLite for accounts/migrations plus PostgreSQL offline SQL generation. Anonymous HTTP/browser regressions additionally passed with DATABASE_URL unset, proving that this flow remains database-independent. Real PostgreSQL tables/indexes/FKs, driver/timezone/NUMERIC behavior, ownership/persistence/security scenarios, rollback/concurrency and migration round trips remain unverified. No migration/model fix is claimed without runtime evidence; see VERIFICATION.md and the conditional runbook in AUTH_AND_USERS.md. This checkpoint is not Phase 4.
