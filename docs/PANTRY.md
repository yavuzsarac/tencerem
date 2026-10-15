# Mutfağım — persistent pantry and preparation audit

## Model and API
Each authenticated user has at most one saved entry per canonical ingredient. Fields: UUID, owner FK, canonical ingredient ID, nullable paired Decimal quantity/unit, optional user-entered expiration_date, UTC created/updated timestamps. Owner IDs are never client-selected. IDs remain private transport identifiers; the UI shows Turkish names and preparation states.

GET /api/v1/me/pantry lists only current-user entries. POST adds (201); duplicates return 409. PATCH by UUID edits quantity/unit/date; DELETE removes (204). Other users' and nonexistent IDs both return 404. Registered ingredient validation, Phase 2 quantity constraints and paired-null rules apply. Zero stock is valid. Presence-only is quantity=null/unit=null, not unlimited stock. No expiry is inferred; dates are informational and do not certify food safety or auto-remove stock.

Compatible unit changes use the Phase 2 normalization service: changing 300 g to kg without a new quantity produces 0.3 kg, preserving stock. Supplying a new compatible-unit quantity is an explicit edit. Mass-to-volume, count-to-mass or cross-culinary changes are rejected for a quantified existing entry. To correct an uncertain original record, explicitly save both quantity/unit as null, then enter a newly verified amount/unit. No guessed density conversion occurs. This initial pantry model has no separate lots or multiple simultaneous incompatible components for one ingredient; future lot modeling requires a migration, not duplicate-stock guessing.

## Basket integration
POST /api/v1/me/baskets/preview accepts recipes/servings, optional_policy and optional pantry_adjustments. It loads only current-user saved entries, applies request-only replacements, then calls the **same** Phase 2 preview_basket service. No duplicate engine exists. Saved diet/allergy conflicts reject unsafe/incomplete selections before calculation. The old /api/v1/baskets/preview still takes explicit pantry and requires no login, preserving anonymous/API tests.

The logged-in ingredient review defaults to Mutfağım, so no quantities need re-entry. The user can explicitly switch to the manual anonymous-style preview; that mode is profile-independent and does not save stock. Both previews leave inventory unchanged. Checklist state remains local. Unknown quantities remain conservative; duplicate adjustment IDs are rejected; original saved amounts survive temporary adjustments. User-entered dates are returned but are not used to infer freshness or automatic allocation priority.

## Targeted 24-recipe / 37-ingredient audit
- Chicken breast is raw; no cooked-chicken identity or raw↔cooked conversion is inferred. “Pişmiş tavuk” is not an alias for raw chicken.
- Rice and pasta are dry/uncooked. Cooked rice/pasta cannot be merged with those IDs. The saved UI visibly labels preparation state; quantities have no cooked-yield conversion.
- cooked_chickpea, cooked_white_bean and green_lentil are explicitly cooked. Recipes already require previously cooked/sieved legumes and explain that soaking/boiling dry legumes is not included in their short timings. The ambiguous green_lentil alias was tightened to explicitly cooked names.
- Legacy anonymous `nohut`/`kuru fasulye` presence aliases remain for backwards compatibility. They still make no quantity claim. Persistent entry uses the canonical selector “Haşlanmış … · Pişmiş / haşlanmış”; users must not enter dry stock under that identity. Introducing separate dry legume IDs/recipes is future work, not an implicit substitution.
- Other vegetables/eggs/meat are raw; grains and red lentil are dry. Dairy/oils/seasonings are ready-to-use. Salt is not labeled “uncooked.” Metadata is intentionally small, not a preparation-state ontology.
- Counts vs grams (e.g. tomato, potato, carrot) and culinary-vs-metric requirements remain explicit. Default measurement dimension is a hint and never a conversion rule.
- Optional yogurt/dairy garnishes affect allergy/diet eligibility even if the basket excludes optional ingredients; this is conservative by design.
- Reviewed quantities/times/steps for all 24 recipes; no obvious arithmetic defect requiring culinary rewrites was found. Base servings, ingredient quantities, instructions and recipe IDs were not rewritten. Source formulations remain internally authored and not professionally kitchen-tested; duration and yields remain estimates.

No numeric food conversion or broad culinary change was made during this audit. Metadata and one ambiguous cooked-lentil alias changed; inherited presence aliases and their limits are documented. API tests confirm original recipe/basket behavior, and saved basket acceptance verifies 500 g chicken minus 300 g = 200 g, rice 300 g covered by 500 g, and unknown salt without false coverage.
