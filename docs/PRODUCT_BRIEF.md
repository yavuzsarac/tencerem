# Tencerem product brief

## Users and problem
Türkiye-based home cooks, busy households, and budget-conscious meal planners spend time deciding what to cook and translating recipes into affordable shopping lists.

## Proposed solution
A Turkish-first meal planner combining preferences, metric recipes, pantry inventory, and consolidated grocery baskets in TRY. AI and retailer data are future capabilities.

## Confirmed Phase 0 scope
A responsive preference form submits craving, servings, maximum basket budget, maximum preparation time, and dietary preference to an API. The API validates and echoes preferences with an explicit development notice. No preferences are stored. Liveness works independently of PostgreSQL; readiness actually probes PostgreSQL when configured.

## MVP direction and differentiators
Future MVP: grounded recipes, pantry subtraction, consolidated ingredient quantities, and transparent basket estimates. Local cuisine, Turkish product names, metric conversions, and transparent price provenance are intended differentiators, not current capabilities.

## Initial success metrics
Phase 0: valid submissions complete; invalid inputs fail consistently; no simulated recipe or live-price claims. Pilot targets to validate later: 80% unaided preference completion, median completion under two minutes, and 60% recipe usefulness feedback from ten consenting test households. These are targets, not observed results.

## Risks and assumptions
Assume anonymous single-session use, TRY only, 1–12 servings, 5–240 minutes, and up to ₺100,000 per basket. Budget is a preference, not a price guarantee. Dietary preferences are not allergy safety guarantees. Recipe reliability, ingredient normalization, retailer permissions, price freshness, and viable unit economics require validation. No scraping or commercial retailer relationship is assumed.


## Confirmed Phase 1 capability
The original Phase 0 scope above is historical. Tencerem now matches preferences against 24 locally authored recipes with total-time/diet filters, deterministic ranking, serving scaling and named pantry presence. The UI separates available/missing ingredients, shows provenance and instructions, and labels the future basket action unavailable. There are no AI calls, nutritional calculations, live prices or persistent user records. Recipe formulations still need real kitchen/pilot feedback; software validation does not establish culinary quality.


## Confirmed Phase 2 capability and product principle
“Ne yiyeceğini düşünme. Tencerem düşünsün.” Tencerem now recommends one meal first, supports controlled alternatives and acceptance, and connects recipes to quantity-aware pantry comparison and an ingredient basket preview. Safe compatible-unit arithmetic, conservative unknown-quantity handling, optional policy, recipe provenance and local checklists are implemented. Multiple selected recipes can consolidate through the API. This remains an ingredient requirement product without retailer SKUs, prices, live integrations, accounts or persistent inventory. Prior confirmed-scope sections are retained as phase history.


## Confirmed Phase 3 capability
Accounts, persistent preferences (diet, separate allergy exclusions, likes/dislikes and qualitative goals/defaults), Mutfağım quantities/presence/optional dates, and deterministic personalized meals now exist. Today's intent remains separate and ephemeral. Anonymous recommendation and explicit basket previews remain available. Inherent allergen review plus fail-closed incomplete metadata does not guarantee product-label or cross-contact safety. No personal demographic/contact fields beyond email are collected. Software persistence/migrations were tested with isolated SQLite and PostgreSQL SQL generation; a real PostgreSQL deployment was unavailable and remains unverified.

## Confirmed Phase 4 capability
Tencerem adds optional AI-assisted Turkish intent interpretation and selection from deterministically filtered curated recipes, with one primary choice, short grounded explanation, session alternatives and refinement. No generated recipe, nutrition or price information exists. Without provider configuration the app remains usable through a clearly labeled limited rule-based interpreter and the original structured form. Accounts/preferences/pantry and arithmetic keep their existing boundaries. Real provider quality and actual PostgreSQL runtime remain unverified; offline/mock tests do not establish either. Next pilot metrics should measure understood-intent accuracy, accepted recommendations, alternative repetition and fallback frequency without storing private prompts by default.

## Confirmed Phase 5 capability
The ingredient basket now feeds a deterministic internal shopping estimate: canonical products, package combinations, surplus, exact TRY arithmetic and comparison across two explicitly labeled demo markets. Pantry and multi-recipe consolidation precede purchasing. Missing products/unsafe units remain visible, and partial baskets cannot appear cheaper through omitted items. The 65 product snapshots are authored development data, not researched prices, live offers, real retailer integrations or purchasable orders. Price math is independent of AI; existing budget preference does not become a numeric recipe-ranking guarantee. Real PostgreSQL/live AI remain unverified. Phase 6 is not started.
