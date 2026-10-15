# Curated recipe engine — Phase 1

## Data and contracts
`app/data/ingredients.json` defines stable canonical ingredient identifiers, Turkish labels, exact aliases and simple animal/meat/gluten flags for catalog consistency checking. `recipes.json` holds 24 recipes authored for the development application: poultry, pasta, pilav/bulgur, soups, legumes, eggs, meat, vegetables, salads and breakfast. All currently use a four-serving base. Cuisine is Türkiye / ev mutfağı; descriptions and steps are Turkish. Tags include quick/economical/protein-source descriptors; these are qualitative editorial tags, not verified price or nutritional calculations.

Frozen Pydantic models with tuple collections preserve recipe immutability. Each recipe has ID, slug, name, description, cuisine, category, tags/dietary tags, preparation/cooking/total minutes, difficulty, base servings, structured ingredient quantities/units/optionality/notes, steps, and provenance. Nutrition is intentionally omitted. Provenance is `curated_internal`, attributed to Tencerem development catalog, version 1, with an explicit note that formulations have not been professionally kitchen-tested. It never implies an external source.

`RecipeCatalog` loads and validates local JSON when the app is created, so malformed data stops startup. Validation rejects duplicate recipe IDs/slugs, duplicate ingredient identifiers, ambiguous aliases, unknown ingredient references, mismatched labels, invalid units or quantities, invalid serving counts/times, inconsistent total time, empty ingredients/instructions, and contradictory dietary tags. Optional ingredients also participate in diet checks: a dairy garnish prevents vegan labeling. New catalog edits must pass these validations and tests.

The list endpoint returns base recipes. Detail returns `{recipe, requested_servings, scaled_ingredients}`. Recommendation results extend that structure with `available_ingredients`, `missing_ingredients`, `score`, and `reasons`. The base recipe retains base quantities; consumers must use `scaled_ingredients` or its available/missing partitions for the selected servings. Decimal quantities serialize as JSON strings.

## Controlled units and scaling
| Internal unit | Turkish display |
| --- | --- |
| g / kg | g / kg |
| ml / l | ml / l |
| adet | adet |
| tbsp | yemek kaşığı |
| dessert_spoon | tatlı kaşığı |
| tsp | çay kaşığı |
| cup | su bardağı |

No conversions are performed, including spoon/cup volume assumptions or ml-to-g density guesses. Unit choices remain attached to ingredient identity. Each quantity is `base quantity * requested servings / base servings`, computed in a local Decimal context (28 digits), half-up quantized to six decimal places for the API. Scaling always starts from the original recipe and never chains from a prior scaled result. Display uses two decimal places, ROUND_HALF_UP, trailing zero removal, and Turkish decimal comma; a positive amount rounding to zero displays as <0,01 rather than falsely showing zero or inflating it to a minimum quantity. Display rounding is for people, not arithmetic. API quantities are also bounded-precision values; Phase 2 should aggregate before final display rounding and must not parse display strings.

Fractional pieces are retained (e.g. 1,5 eggs), with UI guidance to divide or weigh them; there is no automatic rounding up that would alter proportions. Ingredients preserve their units and notes. Times and instructions are not numerically scaled: pot size, batch size and doneness affect actual time. Steps reference the method while the scaled list is the quantity authority. Serving counts are limited to 1–12.

## Normalization and pantry presence
Normalization trims/collapses whitespace, tolerates Turkish dotted/dotless I, lowercases, folds Turkish diacritics for comparison, and extracts ASCII alphanumeric tokens without heavyweight NLP. Display text is preserved in the catalog. Pantry splits on commas, ignores empty values, deduplicates normalized input and then canonical identifiers, and resolves **exact whole-entry** canonical names/IDs/aliases. No substring match turns `tavuk suyu` into chicken breast. `pirinç, PİRİNÇ, pirinc` yields one rice ID.

Aliases are intentionally small and explicit. `tavuk` maps to chicken breast; `nohut` and `kuru fasulye` map to cooked ingredients and the UI warns that preparation state must be checked. Quantities, stock levels, expiration, ingredient substitutions and preparation transformations are not inferred. Unrecognized text remains visible and contributes no score. Every scaled ingredient is in exactly one available/missing list; optional ingredients remain marked. Water and seasoning are never silently assumed present.

## Deterministic recommendation algorithm
1. Hard-filter recipes whose **total** minutes exceed `max_prep_minutes` (legacy field name). Hard-filter incompatible diet tags. `none` imposes no diet restriction.
2. Normalize the craving into distinct tokens; remove the small documented stop-word set in `recommendation.py` (`bir`, `yemek`, `istiyorum`, `olsun`, `ve`, `ile`, `icin`, `canim`, `bugun`, `bana`).
3. Add text scores for each distinct overlapping token: name **10**, category **6**, tags **4**, ingredient display names **2**. A token may count in multiple fields. Add **2** per canonical ingredient whose full alias-token set occurs in the query and whose ID occurs in the recipe; duplicate aliases do not multiply this score.
4. If non-stop-word query tokens exist, require positive text relevance. Unknown specific queries yield an empty response; no unrelated fallback silently overrides the query. If all tokens are stop words, compatible recipes may be returned using pantry/tie-breaks.
5. Add **3** per distinct pantry ingredient matched in the recipe, including optional items. No pantry quantity sufficiency is asserted. Budget does not participate.
6. Sort by descending score, then ascending total minutes, then ascending ASCII slug; return up to `limit` (default 5, maximum 10). Servings affect quantities, not rank/time. Return understandable Turkish reasons for the query, time, selected diet and pantry matches.

Example: `tavuk sote` for the query `tavuk` scores 10 name + 6 category + 4 tag + 2 ingredient token + 2 canonical alias = 24 before pantry. These weights are product defaults, not a trained model or validated measure of user satisfaction. Current reasons summarize matched field types; there is no model inference.

## Known limitations and next boundary
This is a 24-recipe development catalog, not an exhaustive culinary search engine. There is no stemming, fuzzy spelling, negation understanding, semantic matching or allergy guarantee. Multi-word queries use OR-style relevance signals, not all-token requirements. Diet tags describe this formulation and cannot verify product cross-contamination. Time estimates are approximate and assume ingredients in the stated preparation state. Pantry names carry no quantities. No AI, persistence, prices, retailers, shopping checkout or basket creation exists.

Phase 2 can consume canonical ingredient IDs, original quantities/units, scaled quantities and explicit pantry partitions to consolidate a local grocery list across recipes. It must define compatible-unit conversions, prepared-vs-dry semantics, optional-item policy, pantry quantities and rounding/aggregation before making purchase-quantity claims. Real products/prices remain a separate authorized integration milestone.


## Phase 2 integration (current; prior sections document Phase 1)
Recipe endpoints and ranking retain their Phase 1 contracts. Name-only available/missing lists remain conservative presence signals, while quantity-aware allocation now lives in the basket service. The shared registry supplies ingredient identity/aliases and measurement metadata. The UI presents one ranked meal and alternatives sequentially, then acceptance and quantity review. Phase 2 safely normalizes kg/g and l/ml in baskets, while the original recipe scaling service still preserves source units. See BASKET_ENGINE.md for quantities, policies, provenance and current preview behavior; historical statements above that a basket does not exist are superseded by this completed phase.


## Phase 3 integration
Authenticated /me/recipes/recommend now composes saved safety/diet constraints and MealIntent around the preserved anonymous ranker. See PERSONALIZATION.md for the hierarchy and allergy metadata limits; source recipe quantities/IDs are unchanged.
