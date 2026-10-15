# Roadmap

1. Foundation (completed Phase 0): documented monorepo, Turkish preference form, honest development receipt, health semantics, local PostgreSQL configuration, automated API checks and frontend checks.
2. Curated recipe slice (completed Phase 1): 24 recipes, validated domain schemas, metric/household units, immutable serving scaling, deterministic text/diet/time/pantry ranking, recipe list/detail/recommend APIs and Turkish result cards. No LLM or nutrition claim. Automated and live acceptance checks are recorded in VERIFICATION.md.
3. Ingredient intelligence and basket (completed Phase 2): shared registry, controlled dimensions and safe canonical conversion, independent recipe scaling, quantity consolidation, conservative pantry allocation, unknown/ambiguous statuses, optional policy and provenance. API supports multiple selections; UI presents one meal, acceptance, quantity review and a real ingredient basket preview with local checklist. Tests/actual checks are in VERIFICATION.md.
4. Accounts, Mutfağım and deterministic personalization (Phase 3 implemented/verified at the documented isolated-test level): initial Alembic schema, opaque-cookie accounts, saved preference/allergy constraints, quantity pantry editing, preparation audit and saved-stock baskets. Real PostgreSQL verification remains an explicit open deployment dependency.
5. Production readiness (recommended Phase 4, not started): exercise real PostgreSQL upgrade/rollback/concurrency/backups, add deployment-grade abuse/security controls and observability, define email verification/recovery, account deletion/export and retention/privacy flows, then run kitchen/usability pilots. Acceptance requires real PostgreSQL tests, tested recovery/ownership/privacy flows and reviewed HTTPS/secrets/backup configuration. No AI or retailer functionality is implied.
6. Authorized retailer integrations: contractual/API access, product mapping confidence, freshness and unavailable-item handling. Acceptance: no unauthorized scraping, auditable price timestamps, reproducible comparison tests.
7. Deployment: CI, versioned migrations, secrets management, backups, monitoring, TLS, rate limits, privacy/consent policies, and restore tests. Acceptance: staging smoke tests, rollback and recovery exercise, security review.
8. Monetization: validate willingness to pay before subscription or affiliate infrastructure. Acceptance: transparent pricing, authorized partner arrangements, account/billing security, explicit consent, measurable retention and sustainable costs.

No date or commercial capability is promised by this roadmap.


Future AI generation is an optional later decision after curated recipe quality and domain validation prove useful. It is not part of Phase 1 or the recommended Phase 4 scope.
