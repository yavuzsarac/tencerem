# Tencerem market pricing engine — Phase 5

**Demo fiyatlar · Geliştirme verisi — canlı fiyat değildir.** All market names, brands, products and price snapshots in this phase are internally authored fixtures. They are not researched offers, integrations or current store inventory. Nothing places an order.

## Domain and storage

The existing recipe catalog → Decimal scaling → pantry allocation → missing basket pipeline is unchanged. Only after `BasketPreview` calculates conservative missing quantities does `services/pricing.py` map them to purchasable packages. `repositories/markets.py` loads `app/data/markets.json` and validates it at application startup. Fixtures use the existing Python package-data pattern; no persistence, database migrations, retailer SDK, new dependency or external service was added.

Two sources: **Tencerem Market A · Demo** (`demo-a`) and **Tencerem Market B · Demo** (`demo-b`). There are **65 product snapshots** covering 30 canonical ingredients, with multiple rice/chicken package sizes. Market A's mushroom is intentionally unavailable, Market B intentionally has no feta, and several registry ingredients have no product. Product mapping is an explicit canonical ingredient ID, never fuzzy text matching. Preparation state follows that identity: dry rice is not cooked rice; cooked legumes are labeled haşlanmış. Product labels and allergen suitability are not certified by this mapping.

`Retailer`: unique ID/slug, Turkish name, active flag, data_source=`curated_demo`, currency=`TRY`.

`Product`: unique ID, retailer ID, name, brand, canonical_ingredient_id, positive package_quantity, physical package_unit, positive package price, currency=`TRY`, availability=`available|unavailable`, timezone-aware observed_at and source=`curated_demo`. All fixture observations use **2026-10-01T00:00:00Z**, explicitly a fixed development-data date, not a live observation. Price means the whole package price, not price/kg. It is assumed tax-inclusive for these fixtures; shipping, minimum-order rules, promotions, loyalty/stock limits, multi-buy discounts and additional fees are not modeled.

Validation rejects duplicate retailer IDs/slugs/product IDs, unknown retailers/ingredients, unsupported currency/status/units, nonpositive/nonfinite values, float inputs, excessive precision, noninteger count packages, missing timezone and package dimensions inconsistent with the canonical ingredient's preferred dimension. At most eight products per retailer/ingredient are allowed. Bad catalog data fails startup/tests loudly. There is no fallback to silently dropping bad entries.

## Quantity compatibility

Reuse `normalize_quantity`: kg→g, l→ml, count→adet. Canonical package quantities are compared with each basket component's normalized unit. Physical packages use only g/kg/ml/l/adet. No density, raw/cooked yield, count/mass, spoon/cup or other contextual conversion is invented.

A recipe's 500 g rice can use a 1 kg package. A 500 ml milk requirement cannot use grams. A salt requirement in tsp cannot use a gram package, even though both are salt. Typical catalog recipes contain tsp/tbsp requirements; unless the user supplies sufficient pantry amounts in those exact units, those components remain explicitly unpriced and markets remain partial. The UI explains the incompatible unit rather than pretending the basket is complete. This limitation is intentional and not “fixed” with guessed spoon capacities or ingredient density.

Each positive missing component produces a pricing line; zero-missing components are omitted. Multiple compatible recipes are already consolidated by Phase 2 before package selection. Incompatible components remain separate. Unknown pantry amounts subtract nothing; the entire conservative remainder may be priced with its original warning. `unresolved` subtraction components are not priced at all. Preview/pricing never consumes saved or request pantry state.

## Exact package selection and bounds

Objective per compatible ingredient/component/market:

1. Lowest total package cost that covers missing quantity.
2. Lowest surplus.
3. Lowest package count.
4. Lexicographically smallest multiset of stable product IDs.

Prices are positive and no cross-ingredient promotions exist, so independently minimizing each component also minimizes the modeled basket subtotal. Package supply is assumed unlimited when availability=available; finite stock counts are not claimed.

For a single option, compute integer-safe ceil(missing/package_quantity), purchased amount, surplus and count × package price. For multiple options, convert exact six-place quantities to integer micro-units and divide package sizes by their GCD. Round the required threshold upward to this reachable lattice. Use unbounded dynamic programming for each reachable exact purchased quantity up to `target + largest_package_step - 1`. With positive costs, an optimum cannot exceed this bound: otherwise a whole package could be removed while still meeting the requirement and reducing cost.

Each state stores integer kuruş cost, package count and signed counts in stable product-ID order. Evaluate all covering states using the objective above and reconstruct selected purchases. This handles mixed sizes: a 1400 g need can use a 1 kg plus 500 g package when cheaper than homogeneous alternatives. It does not merely compare one size at a time.

There are at most **20,000 quantity states** and **eight options** per search. Complexity is O(states × options), with O(states × options) compact plan storage. A request is already bounded to 20 selected recipes and the fixed small catalog. A search exceeding the cap returns `optimization_limit`, no approximate “cheapest” claim and no full basket total. Especially small/coprime package sizes or extreme requests can trigger this explicit limit. Single-option calculations do not allocate a large DP array. Future larger catalogs should revise/test bounds deliberately, not add an external optimization service by default.

Examples (fixture/test values, not actual offers): 700 g / 1 kg at 60 TL → one package, 300 g surplus; 1200 g / 500 g at 90 TL → three packages, 1500 g purchased, 300 g surplus, 270 TL. 700 g with 500 g/50 TL versus 1 kg/80 TL chooses 80 TL. 900 g with 500 g/30 TL versus 1 kg/70 TL chooses two smaller packages at 60 TL.

## Money

Catalog/API money is Decimal from decimal strings, positive and at most two fractional places. Floats are rejected for product price/package quantities. Optimization uses exact integer kuruş; totals and purchased quantities use an isolated 28-digit Decimal context. Monetary response fields serialize as fixed two-place strings, e.g. `"106.00"`. Unknown/unpriced line totals and incomplete full-basket totals are **null**, not free items. The frontend formats validated strings directly into `106,00 TL` without binary floating-point arithmetic or summing prices in JavaScript.

## Priced basket and completeness

`Purchase` retains the full product/provenance, package_count, normalized purchased_quantity and package line_total. A `PricedItem` includes canonical ingredient/name, optional status, conservative required_missing_quantity, normalized unit, original calculation status, fulfillment status, selected purchases, aggregate package count, purchased quantity, surplus and line total. Multiple package products can appear in one line.

Statuses: `fulfilled`, `unavailable`, `incompatible_unit`, `unresolved`, `optimization_limit`. Unpriced lines retain their required quantity, empty purchases, null purchased/surplus/price and a Turkish explanation. They remain in coverage metrics.

`MarketEstimate` includes retailer, lines, total_required_ingredients, fulfilled_count, unavailable_count, complete, priced_subtotal, basket_total, currency and demo warnings. Counts are unique **missing ingredients**, not all recipe ingredients, components or SKUs. An ingredient with multiple components counts as fulfilled only if every positive missing component is fulfilled. `unavailable_count` includes all not-fully-fulfilled ingredients regardless of reason; it does not specifically claim a stock outage.

`priced_subtotal` sums only priced lines. `basket_total` is available only for complete coverage; otherwise null. A partial market with 100 TL priced subtotal cannot beat a complete 140 TL basket. Empty purchases have mathematical total 0.00, but no ingredient is assigned a fake zero price. A fully pantry-covered basket needs no purchases and no market recommendation.

Comparison ranks complete markets first, ascending full basket total, stable retailer ID. Partial markets follow by descending fully fulfilled ingredient count and stable retailer ID; their incomplete subtotals are **not** used to advertise a cheapest basket. If none is complete, recommended_retailer_id=null and the user gets an explicit partial-coverage message. Inactive markets are excluded and cannot be selected through price APIs.

Optional policy comes from the original request: required_only excludes optional contributions before all allocation/pricing; include_optional includes them in the selected basket's completeness. Required/mixed/optional status remains visible. The engine does not silently discard optional shortages after the user chose to include them.

## APIs and owner boundaries

- GET `/api/v1/markets`: active demo sources.
- GET `/api/v1/markets/{retailer_id}/products`: all snapshots for that active market, including explicitly unavailable records.
- POST `/api/v1/baskets/price`: existing BasketRequest fields plus retailer_id; returns mode=demo_market_estimate, authoritative ingredient basket and one estimate.
- POST `/api/v1/baskets/compare`: existing BasketRequest; returns mode=demo_market_comparison, ingredient basket, sorted estimates, recommended_retailer_id, message and demo notice.
- POST `/api/v1/me/baskets/price`: existing SavedBasketRequest plus retailer_id.
- POST `/api/v1/me/baskets/compare`: existing SavedBasketRequest.

Example anonymous comparison:

```json
{
  "recipes": [{"slug": "tavuklu-pilav", "servings": 5}],
  "pantry": [
    {"ingredient_id": "chicken_breast", "quantity": "300", "unit": "g"},
    {"ingredient_id": "rice", "quantity": "500", "unit": "g"},
    {"ingredient_id": "salt", "quantity": "10", "unit": "tsp"},
    {"ingredient_id": "olive_oil", "quantity": "10", "unit": "tbsp"}
  ],
  "optional_policy": "required_only"
}
```

This authored example leaves 200 g chicken plus water to purchase: A=110.00 TRY, B=106.00 TRY, so B wins. Removing quantified spoon stock makes these estimates incomplete, not deceptively cheaper complete baskets.

Clients cannot submit trusted missing totals, product choices or prices; every request recomputes from canonical recipe selections/pantry using the same engine. Unknown markets return actionable 404; invalid recipes/fields return the existing 422 envelope. New POSTs are read-only and use no-store responses. Next forwards only allowlisted price/compare operations with existing bounded bodies/timeouts. Public production ingress/rate/size hardening remains necessary.

Saved routes derive ownership from the existing validated session, accept no user ID and reuse `services/user_baskets.py`, extracted from the previous saved-preview handler without changing its behavior. This loads only that owner's preferences/pantry, enforces saved diet/allergy checks and applies temporary adjustments through the existing overlay. Anonymous requests use explicit pantry and need no database or AI. Persistent preferences, pantry and basket records are not mutated.

## Frontend

After a basket preview, the separate **Tahmini Market Sepeti** section displays the non-live disclaimer before any request. Marketleri Karşılaştır computes estimates for the same selections/pantry/policy. One best complete market is selected first; alternatives stay behind a compact disclosure/select. If partial, no cheapest-market claim is made. Lines show missing amount, actual chosen products, package count, package price, purchase/surplus quantities, totals, source and fixed fixture date. TRY uses Turkish separators. Pending/error/retry, partial/empty states and mobile layout are covered by smoke tests. Changing stock/policy/recipe resets the old preview and price state; local ingredient checklists stay separate.

The original ingredient preview response still contains no product prices; its contract remains unchanged. Prices appear only in the separately requested demo estimate. No checkout, real product availability or order action is shown.

## AI and future adapter boundary

There are **no pricing calls to the AI provider**, no model arithmetic and no market-catalog payload sent to it. Phase 4 remains unchanged and pricing works with AI disabled or absent. A future explanation may consume a small verified comparison summary, but this phase does not claim that a recipe is cheaper than other recipes without evaluating them. Existing economical tags/budget controls are not a numeric budget guarantee and do not rank recipes by these new demo prices.

Future authorized retailer adapters can supply validated price/product snapshots with provenance, timestamps and explicit canonical mapping confidence through the repository boundary. Actual supplier ingredients/allergens, availability freshness, stock, location, taxes/fees and consent need separate contracts/security tests. No retailer network clients, scraping, authentication automation or private endpoints exist here. PostgreSQL runtime and live AI execution are still unverified; Phase 5 does not resolve them. Phase 6 has not started.
