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
