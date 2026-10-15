"""Exact bounded package purchasing. No AI, network or pantry arithmetic here."""
from decimal import Decimal, localcontext
from functools import reduce
from math import gcd
from app.schemas.markets import Purchase, PricedItem, MarketEstimate, ComparisonResponse
from app.services.quantities import normalize_quantity

MAX_STATES = 20000


class OptimizationLimit(ValueError): pass


def optimize_packages(missing, unit, products):
    """Unbounded knapsack on the exact micro-unit/GCD lattice, with explicit caps."""
    with localcontext() as context:
        context.prec = 28
        return _optimize(missing, unit, products)


def _optimize(missing, unit, products):
    if not isinstance(missing, Decimal) or not missing.is_finite() or missing <= 0:
        raise ValueError("Missing requirement must be a positive Decimal")
    products = tuple(sorted(products, key=lambda p:p.id))
    if not products or len(products) > 8: raise OptimizationLimit("Product option limit")
    sizes = []
    for product in products:
        quantity, canonical = normalize_quantity(product.package_quantity, product.package_unit)
        if canonical != unit: raise ValueError("Incompatible package unit")
        sizes.append(quantity)
    # Basket scaling and product schemas have at most six fractional places.
    integer_sizes = [int(size * 1000000) for size in sizes]
    if any(size * 1000000 != integer for size, integer in zip(sizes, integer_sizes)):
        raise ValueError("Unsupported package precision")
    quantum = reduce(gcd, integer_sizes)
    steps = [size // quantum for size in integer_sizes]
    needed_micro = missing * 1000000
    target = int(needed_micro // quantum) + (needed_micro % quantum > 0)
    prices = [int(p.price * 100) for p in products]
    if len(products) == 1:
        count = (target + steps[0] - 1) // steps[0]
        counts = (count,)
    else:
        # Any cost-optimal solution has quantity < target + largest step: if
        # it overshoots by a whole package, removing it reduces positive cost.
        bound = target + max(steps) - 1
        if bound > MAX_STATES: raise OptimizationLimit("Exact package search exceeds state limit")
        # Entry: cost in integer kurus, package count, signed counts by stable ID.
        zero = (0,) * len(products)
        states = [None] * (bound + 1)
        states[0] = (0, 0, zero)
        for amount in range(1, bound + 1):
            best = None
            for index, step in enumerate(steps):
                if step > amount or states[amount-step] is None: continue
                cost, count, negatives = states[amount-step]
                updated = list(negatives); updated[index] -= 1
                candidate = (cost + prices[index], count + 1, tuple(updated))
                if best is None or candidate < best: best = candidate
            states[amount] = best
        feasible = [(state[0], amount-target, state[1], state[2])
                    for amount, state in enumerate(states) if amount >= target and state is not None]
        winner = min(feasible)
        counts = tuple(-n for n in winner[3])
    purchases = tuple(Purchase(product=p, package_count=count, purchased_quantity=size*count,
        line_total=(p.price*count).quantize(Decimal("0.01"))) for p, size, count in zip(products, sizes, counts) if count)
    purchased = sum((p.purchased_quantity for p in purchases), Decimal(0))
    total = sum((p.line_total for p in purchases), Decimal(0)).quantize(Decimal("0.01"))
    return purchases, purchased, purchased-missing, total


def price_basket(basket, market_catalog, retailer):
    with localcontext() as context:
        context.prec = 28
        return _price_basket(basket, market_catalog, retailer)


def _price_basket(basket, market_catalog, retailer):
    lines = []
    for item in basket.items:
        options = market_catalog.options(retailer.id, item.ingredient_id)
        for component in item.components:
            if component.missing_quantity <= 0: continue
            compatible = tuple(p for p in options if normalize_quantity(p.package_quantity,p.package_unit)[1] == component.unit)
            base = dict(ingredient_id=item.ingredient_id, name=item.name, optional_status=item.optional_status,
                required_missing_quantity=component.missing_quantity, unit=component.unit, calculation_status=item.calculation_status)
            if component.calculation_status == "unresolved":
                status, message = "unresolved", "Miktar hesabı çözümlenmedi; fiyatlandırma yapılmadı."
            elif not options:
                status, message = "unavailable", "Bu demo markette uygun ve mevcut ürün bulunamadı."
            elif not compatible:
                status, message = "incompatible_unit", "Ürün birimi ihtiyacı karşılamıyor; yoğunluk veya kaşık/bardak dönüşümü yapılmaz."
            else:
                try:
                    purchases, purchased, surplus, total = optimize_packages(component.missing_quantity, component.unit, compatible)
                    lines.append(PricedItem(**base,status="fulfilled",purchases=purchases,
                        package_count=sum(p.package_count for p in purchases), purchased_quantity=purchased,
                        surplus_quantity=surplus,line_total=total,message="Eksik miktarı karşılayan en düşük demo paket maliyeti."))
                    continue
                except OptimizationLimit:
                    status, message = "optimization_limit", "Kesin paket seçimi işlem sınırını aşıyor; tahmini en ucuz sonuç uydurulmadı."
            lines.append(PricedItem(**base,status=status,message=message))
    ids = {line.ingredient_id for line in lines}
    covered = {ident for ident in ids if all(line.status == "fulfilled" for line in lines if line.ingredient_id == ident)}
    complete = len(covered) == len(ids)
    subtotal = sum((line.line_total for line in lines if line.line_total is not None), Decimal(0)).quantize(Decimal("0.01"))
    return MarketEstimate(retailer=retailer, items=tuple(lines),total_required_ingredients=len(ids),
        fulfilled_count=len(covered),unavailable_count=len(ids-covered),complete=complete,
        priced_subtotal=subtotal,basket_total=subtotal if complete else None)


def compare_basket(basket, market_catalog):
    estimates = [price_basket(basket,market_catalog,r) for r in market_catalog.retailers if r.active]
    # Partial baskets compare coverage only; a smaller subtotal is not a bargain.
    estimates.sort(key=lambda e:(not e.complete, e.basket_total if e.complete else -e.fulfilled_count, e.retailer.id))
    winner = next((e for e in estimates if e.complete), None)
    needs_shopping = any(c.missing_quantity > 0 for item in basket.items for c in item.components)
    return ComparisonResponse(basket=basket, estimates=tuple(estimates),
        recommended_retailer_id=winner.retailer.id if winner and needs_shopping else None,
        message="Eksik malzeme yok; alışveriş gerekmiyor." if not needs_shopping else
                "Eksiklerin tamamını karşılayan en düşük demo sepet maliyeti." if winner else
                "Hiçbir demo market eksiklerin tamamını karşılamıyor. Kısmi tutarlar tam sepet fiyatı değildir.")
