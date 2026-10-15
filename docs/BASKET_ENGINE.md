# Ingredient intelligence and basket engine — Phase 2

## Product boundary
“Ne yiyeceğini düşünme. Tencerem düşünsün.” The primary flow is one deterministic meal recommendation, acceptance, recipe review, pantry quantity review, then an ingredient basket preview. Alternatives remain ranked on the backend and are exposed one at a time through Başka Öner. Basket items represent **ingredient requirements, never supermarket SKUs**. There are no prices, retailer names/products, checkout, AI calls, accounts or persistence.

## Shared ingredient registry
`IngredientDefinition` retains stable Phase 1 IDs, Turkish names, exact aliases and diet-consistency flags, and adds category, preferred measurement dimension, default basket unit and quantity_subtraction_supported. All 37 entries in `data/ingredients.json` have explicit metadata. `IngredientRegistry` owns ID lookup and exact normalized alias resolution; legacy pantry normalization delegates to it too. The catalog validates every ingredient reference and label, dietary flags, duplicate IDs/slugs, ambiguous aliases and default-unit/dimension consistency on app creation. Orphans fail loudly.

Preferred dimension and display unit are hints, not conversion instructions. Tomatoes may be measured in count or mass; neither representation implies the other. No ingredient density table or automatic preparation-state transformation is introduced. `tavuk`, `tavuk göğsü`, `tavuk gogsu` share one breast ID. `tavuk suyu` does not match it. Existing cooked-legume aliases are retained for Phase 1 compatibility: recipe notes and the editor explicitly require checking preparation state before entering stock quantities.

## Quantities and safe conversions
- MASS: g and kg normalize to **g**, factor 1000 for kg.
- VOLUME: ml and l normalize to **ml**, factor 1000 for l.
- COUNT: adet remains **adet**, including fractional counts inherited from recipe scaling.
- CULINARY: tbsp, dessert_spoon, tsp, cup remain independent contextual units. Their Turkish labels are yemek kaşığı, tatlı kaşığı, çay kaşığı, su bardağı.

Only identical canonical units combine. There are **no** g/ml, count/mass, cup/gram, cup/ml, or spoon/spoon assumptions. `500 g + 1 kg` becomes `1500 g`; `500 ml + 1 l` becomes `1500 ml`; `2 adet + 3 adet` becomes `5 adet`. `500 g flour + 1 cup flour` stays as two components on one ingredient item, marked incompatible_units. Matching stock can still be subtracted independently from each compatible component; no scalar total across incompatible units is fabricated.

All calculation uses Decimal under a local precision-28 context. The existing scaling service supplies six-decimal, half-up quantities from original recipe values. Basket addition/subtraction uses those numeric quantities, never display strings, and applies no further two-decimal display rounding. Display trims insignificant zeros and uses Turkish decimal commas. This keeps basket explanations and small shortages visible. Nonterminating serving ratios inherit Phase 1's six-place approximation; exact means arithmetic is resolved at that declared precision, not that kitchen measurements or recipe quality are certified.

## Request contract
`POST /api/v1/baskets/preview` accepts:

```json
{
  "recipes": [
    {"slug": "tavuklu-pilav", "servings": 3},
    {"slug": "tavuk-sote", "servings": 2}
  ],
  "pantry": [
    {"ingredient_id": "chicken_breast", "quantity": "0.4", "unit": "kg"},
    {"ingredient_id": "salt", "quantity": null, "unit": null, "presence": true}
  ],
  "optional_policy": "required_only"
}
```

Between 1 and 20 selections are allowed; each has a catalog slug and integer servings 1–12. Repeating a slug is allowed and intentionally adds another requirement; selection_index distinguishes contributions from repeated meals. Pantry allows at most 200 entries, canonical ingredient IDs, finite Decimal quantities from 0 through 1,000,000,000 with at most six fractional digits, and a controlled unit. Decimal strings are recommended for clients. Quantity/unit must be both present or both null. presence defaults to true; false is rejected—omit absent stock instead. Unknown fields are rejected. Invalid/unknown slugs, IDs, units, amounts or policies return the existing 422 error envelope with actionable error.fields. Unknown recipe slugs here are invalid selections (422); the preserved detail endpoint still uses 404.

`GET /api/v1/ingredients` exposes the registry for clients without accepting ad-hoc ingredient identities. The Next same-origin `/api/baskets/preview` proxy shares timeout/error handling with Phase 0/1 and has a 64 KiB body check; the original proxy routes keep their 8 KiB checks. Application field limits remain enforced on direct FastAPI calls. These checks do not replace public ingress limits.

## Pantry semantics and duplicate policy
Known stock is normalized into a new inventory; neither request pantry nor recipes are mutated. For each ingredient/unit bucket after all selected recipe requirements are consolidated:

`allocated = min(required, known available)`

`missing = required - allocated`

Excess available stock remains reported as available; allocated never exceeds the requirement. Zero stock is valid and allocates zero. Missing never goes negative. No stock is consumed merely by previewing or checking a shopping-list box.

Unknown quantity is `{quantity:null, unit:null, presence:true}`. It subtracts **nothing**. The item says “Evde var · miktar bilinmiyor”; missing is a conservative unconfirmed remainder, not a claim that the entire quantity must be purchased. Known stock and a single unknown-presence entry may coexist; only the known amount is deducted. If the known amount already fully covers a component, that component remains exact while the unknown-stock note stays visible.

Two quantified entries for the same canonical ingredient and compatible unit group are rejected, including `500 g` plus `0.5 kg`, because they may describe the same stock twice. The client must combine genuinely separate lots explicitly before submission. Duplicate unknown-presence entries are also rejected. Distinct incompatible components (e.g. grams and cups) may coexist; each is shown, never converted. Unused registered pantry entries do not create basket requirements. If quantity_subtraction_supported is false, stock remains visible but allocation is zero and status is unresolved.

## Consolidation and optional ingredients
1. Resolve each selection from the validated catalog.
2. Scale independently for its requested servings, preserving original recipes.
3. Default policy **required_only** excludes every optional contribution; response records how many were excluded. **include_optional** includes them explicitly.
4. Normalize only safe unit pairs, then group by canonical ingredient ID and normalized unit.
5. Sum numeric contributions, retaining source selection index, recipe ID/slug/name/servings, original scaled quantity/unit, normalized quantity/unit, optional flag, notes and recipe provenance.
6. Allocate pantry once per consolidated bucket; never reuse stock separately for each recipe.
7. Return one item per ingredient, separate unit components, calculation warnings and deterministic summary. Items sort by ID, components by canonical unit; recipe contribution order follows the request.

If one recipe requires an ingredient and another has it optionally, included contributions are marked mixed and retain separate mandatory_quantity and optional_quantity sums. required_quantity means the total included need, including optional portions only when requested. There is no per-recipe pantry allocation claim; source quantities explain the requirement, while stock is allocated at consolidated component level.

## Response model and calculation status
Basket contains mode=ingredient_preview, selected_recipes, optional_policy, excluded_optional_contributions, items, warnings and summary. Each item has ingredient_id/name/category, optional_status (required/optional/mixed), pantry_stock (including incompatible components and unknown presence), unknown_pantry_quantity, calculation_status and warnings. Because not all units can combine, quantities live in **components**, not a misleading single ingredient total.

Each component includes unit/label, required_quantity, mandatory_quantity, optional_quantity, pantry_available_quantity (null for unknown-only compatible stock), pantry_allocated_quantity, missing_quantity, display strings, explanation and recipe contributions. pantry_stock shows all submitted stock for that ingredient, while pantry_available_quantity is only the known compatible bucket (zero if absent, even when incompatible stock exists).

- **exact:** compatible numeric calculation resolved at the documented scaling precision; not a recipe-quality or medical claim.
- **presence_only:** some remaining requirement has only unquantified possible coverage. Unknown amount is not subtracted.
- **incompatible_units:** item has multiple incompatible positive requirement/stock unit components. Each component can still have exact compatible arithmetic; the item warns that they cannot be merged into one total. Positive incompatible stock is shown explicitly.
- **unresolved:** subtraction is disabled for that ingredient. Entire included requirement stays as missing/control-needed.

Item status precedence is unresolved, incompatible_units, presence_only, exact. A zero-amount stock in a mismatching unit does not create a conversion warning. Warnings can coexist: unknown stock is still reported even if incompatible_units takes precedence.

## Summary and checklist
Summary counts unique canonical ingredients, selected recipe entries and sum of selected servings, fully_covered (all components missing zero and item exact), partially_covered (some confirmed stock allocated and some shortage remains), items_to_buy (any positive conservative shortage), and unresolved_items (any non-exact item, including presence-only). Counts intentionally overlap: a partially covered or unresolved ingredient may also need buying/checking. They are not SKU counts or prices. Fully covered excludes ambiguous items conservatively.

The frontend accepts one meal at a time, exposes source recipe/provenance and estimated duration, and labels initial pantry coverage as unverified name matches. After acceptance it shows the recipe and a quantity editor; optional ingredients default off. Stock edits or policy changes invalidate the old basket. Basket output shows required, known available, allocated and missing/control-needed amounts, calculation details, source recipes, warnings and a local checkbox for each positive missing component. Checkboxes live only in React state; refreshing, changing the meal or recalculating resets them. No backend persistence or inventory deduction occurs. Multi-recipe baskets work through the API; there is no weekly planner UI.

## Acceptance coverage and limitations
Automated fixtures cover exact mandatory scenario A (500 g chicken minus 300 g; 300 g rice covered by 500 g; 5 g salt unknown), scenario B (two 300 g chicken requirements share only 400 g stock), and scenario C (500 g flour plus one cup never get density-converted). Synthetic fixtures exercise combinations not present in the development catalog without changing authored recipes. Live catalog integration also exercises the two-recipe 600−400=200 g chicken case. The browser uses five-serving tavuklu-pilav: 500 g chicken, 300 g rice and salt in its authored tsp unit; pantry quantities subtract safely and salt remains unknown.

Recipes remain 24 locally authored, non-kitchen-certified formulations. Name aliases do not verify preparation state, allergens or inventory freshness. Pantry quantities are user declarations; no lot identity, expiry, persistent pantry, product matching, package rounding, money or retailer comparison exists. Household units cannot be converted automatically. Public deployment still needs ingress limits, rate limiting, TLS and operational hardening.

## Recommended Phase 3 extension points (not implemented)
Audit ingredient preparation states and conservative aliases, improve quantity-entry guidance and ingredient validation UX, then run a small kitchen/usability pilot. Acceptance should include explicit cooked/dry distinctions, no silent incompatible substitutions, reliable correction flows and documented feedback on recipe/time assumptions. Current registry IDs, component quantities and recipe contributions provide the boundary for future product matching; do not collapse ingredient requirements into supermarket SKUs or introduce retailer/live-price behavior in this phase.
