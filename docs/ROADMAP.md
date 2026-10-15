# Roadmap

1. Foundation (completed Phase 0): documented monorepo, Turkish preference form, honest development receipt, health semantics, local PostgreSQL configuration, automated API checks and frontend checks.
2. Curated recipe slice (completed Phase 1): 24 recipes, validated domain schemas, metric/household units, immutable serving scaling, deterministic text/diet/time/pantry ranking, recipe list/detail/recommend APIs and Turkish result cards. No LLM or nutrition claim. Automated and live acceptance checks are recorded in VERIFICATION.md.
3. Ingredient intelligence and basket (completed Phase 2): shared registry, controlled dimensions and safe canonical conversion, independent recipe scaling, quantity consolidation, conservative pantry allocation, unknown/ambiguous statuses, optional policy and provenance. API supports multiple selections; UI presents one meal, acceptance, quantity review and a real ingredient basket preview with local checklist. Tests/actual checks are in VERIFICATION.md.
4. Ingredient verification and usability (recommended Phase 3, not started): audit prepared/raw identities and aliases, improve quantity guidance/correction flows, and conduct a small recipe/kitchen usability pilot. Acceptance: cooked/dry distinctions remain explicit, no unsafe substitutions, quantity corrections invalidate old calculations, users understand unknown vs sufficient stock, and recipe/time feedback is documented. No retailer, price, AI, authentication or persistence work is implied.
5. Authorized retailer integrations: contractual/API access, product mapping confidence, freshness and unavailable-item handling. Acceptance: no unauthorized scraping, auditable price timestamps, reproducible comparison tests.
6. Deployment: CI, versioned migrations, secrets management, backups, monitoring, TLS, rate limits, privacy/consent policies, and restore tests. Acceptance: staging smoke tests, rollback and recovery exercise, security review.
7. Monetization: validate willingness to pay before subscription or affiliate infrastructure. Acceptance: transparent pricing, authorized partner arrangements, account/billing security, explicit consent, measurable retention and sustainable costs.

No date or commercial capability is promised by this roadmap.


Future AI generation is an optional later decision after curated recipe quality and domain validation prove useful. It is not part of Phase 1 or the recommended Phase 3 scope.
