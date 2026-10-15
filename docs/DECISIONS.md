# Engineering decisions

- Keep the requested mealpilot-ai directory inside the empty workspace; the product name is Tencerem. No existing user files were replaced.
- Use Python 3.12.14 and Node 24.19.0 found in Codex's bundled runtime. System Python is only a non-working Windows alias; no system runtimes were replaced. Git is bundled. Docker is unavailable.
- Use Next 16/React 19, TypeScript, FastAPI/Pydantic 2, SQLAlchemy 2, psycopg 3, and Alembic. Frontend lockfile and backend requirements lock capture the installed versions. Backend pyproject retains compatible bounds; use the lock for reproducibility.
- Keep API and frontend separate, with a thin Next same-origin proxy. This avoids exposing internal backend addresses in browser configuration and keeps backend business validation reusable. The extra HTTP hop is acceptable at this scale.
- Return an explicit stateless development receipt instead of invented recipes. No database is needed to validate preferences.
- Separate liveness from strict DB readiness. A missing DB is never reported as connected.
- Use CSS and system fonts with a small decorative pot illustration; no font CDN, image downloads, animation library, or design-system dependency.
- Do not create unused services/repositories/models or an empty Alembic environment. Add them with the first real domain behavior/schema change.
- Docker Compose runs only PostgreSQL; application processes run locally for short feedback loops. Docker execution cannot be verified here.
- No authentication or public deployment; deployment hardening belongs to its explicit milestone.

Dependency references: [Next installation requirements](https://nextjs.org/docs/app/getting-started/installation), [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/). Resolved versions are recorded from actual package installation, not inferred from these pages.


## Phase 1 decisions — 2026-10-15
- Product references already used Tencerem; repository path `mealpilot-ai` remains for compatibility. Search found no obsolete user-facing MealPilot AI branding.
- Keep Phase 0 endpoints, config, DB probes, Compose and API validation tests. Add recipe routes and real domain services without replacing the architecture.
- Use 24 locally authored JSON recipes and 37 canonical ingredient definitions, loaded and validated on app creation. Include JSON as Python package data. No runtime dependency or database change was necessary.
- Use frozen Pydantic models and tuple collections, positive Decimal quantities, a controlled unit enum, coherent times and stable IDs/slugs. Reject malformed catalog data rather than silently hiding broken recipes.
- Use total time as the hard time constraint while retaining the existing `max_prep_minutes` wire name for compatibility. Document and label the total-time meaning in the UI.
- Permit two-character cravings such as `et` on the new recommendation endpoint/UI; leave Phase 0's existing minimum intact. Keep optional max_budget_try validated but explicitly unapplied because there is no price model.
- Apply diet filters before deterministic text and pantry scoring; resolve ties with duration and slug. Return empty results for unmatched specific text instead of implying a valid personalized fallback. Exact weights and limitations are in RECIPE_ENGINE.md.
- Pantry is name-based presence only, with exact aliases and unknown entries surfaced. Prepared/dry states and pantry quantities are not inferred. Salt, water and optional items remain explicit.
- Scale from base quantities using Decimal and half-up six-place API/two-place display rounding. Never convert density-dependent units. Preserve fractional pieces; times remain estimates.
- Share the Next proxy implementation, keep API reasons/provenance visible, and disable Sepete Hazırla with a Phase 2 explanation. No fake basket, AI or prices.
- Keep tests in the existing pytest stack and use existing bundled Playwright/Edge for browser acceptance, avoiding additional frontend test dependencies. Set pytest basetemp to the dedicated ignored project cache because the Windows global pytest temp directory is inaccessible in this environment.
- No Phase 0 commit existed. All original files were already untracked. Do not stage/commit/push automatically or manufacture a historical baseline; recommend a reviewed combined initial checkpoint unless a genuine Phase 0 snapshot is supplied.


## Phase 2 decisions — 2026-10-15
- Preserve all Phase 0/1 endpoints and test coverage; no database or dependency/system changes. Extend the existing 37-ingredient data, rather than introduce a second identity catalog.
- IngredientRegistry becomes shared alias/ID lookup, with explicit categories, measurement hints and subtraction capability. Preferred units never imply ingredient density or preparation-state conversion.
- Safe canonical arithmetic uses Decimal grams, milliliters and counts. Every culinary unit remains its own component. No general conversion table guesses spoon/cup volumes.
- One basket item per canonical ingredient, with quantity components when needed. This avoids pretending grams and cups can share one numeric total and preserves a future retailer-matching boundary without implementing SKUs.
- Allocate pantry after all requirements consolidate. Unknown quantity subtracts nothing; duplicate compatible pantry buckets are rejected instead of silently summing potentially duplicate stock. A repeated selected recipe intentionally represents an additional meal and retains its selection_index.
- Required-only is the default. Included optional and mandatory contributions remain distinguishable, including mixed ingredients. Source recipe metadata/quantities/units/notes survive consolidation.
- Reuse Phase 1 scaling precision; do not calculate from two-decimal display strings. Basket displays retain significant precision and trim zeroes. Exact status means resolved arithmetic at this precision, not cooking/allergen guarantees.
- Summary counts are ingredient based and deliberately overlapping where partially covered or unresolved shortages remain. Unknown stock is not counted as fully covered.
- Keep multiple ranked backend candidates but show one meal, explicit acceptance, recipe review, quantity editor and basket. Local checkbox state resets when recalculating. Multi-recipe preview is API-capable; no weekly planner UI was added.
- Add a 64 KiB Next basket proxy limit while retaining the original 8 KiB preference limits; existing timeout/error behavior remains shared. Production ingress hardening remains separate.
- Recommend a combined Phase 0+1+2 initial checkpoint because no earlier commits exist. Do not fabricate intermediate history or stage/push user files automatically. Phase 3 is not started.
