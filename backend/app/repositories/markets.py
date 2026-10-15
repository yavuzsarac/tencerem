"""Local authored product/price snapshots; no network or fuzzy product matching."""
import json
from pathlib import Path
from app.schemas.markets import Retailer, Product
from app.services.quantities import dimension

DATA = Path(__file__).resolve().parents[1] / "data" / "markets.json"


class MarketCatalog:
    def __init__(self, registry, path=DATA, *, retailers=None, products=None):
        if retailers is None or products is None:
            data = json.loads(path.read_text(encoding="utf-8"))
            retailers = tuple(Retailer.model_validate(r) for r in data["retailers"])
            products = tuple(Product.model_validate(p) for p in data["products"])
        self.retailers, self.products = tuple(retailers), tuple(products)
        self.validate(registry)
        self._retailers = {r.id:r for r in self.retailers}
        self._products = {}
        for product in sorted(self.products, key=lambda p:p.id):
            self._products.setdefault((product.retailer_id, product.canonical_ingredient_id), []).append(product)

    def validate(self, registry):
        if not self.retailers: raise ValueError("Market catalog must have retailers")
        for field in ("id", "slug"):
            if len({getattr(r,field) for r in self.retailers}) != len(self.retailers):
                raise ValueError("Duplicate retailer identity")
        if len({p.id for p in self.products}) != len(self.products): raise ValueError("Duplicate product ID")
        retailers = {r.id:r for r in self.retailers}
        counts = {}
        for product in self.products:
            ingredient = registry.get(product.canonical_ingredient_id)
            if product.retailer_id not in retailers: raise ValueError("Unknown product retailer")
            if ingredient is None: raise ValueError("Orphan product ingredient")
            if dimension(product.package_unit) != ingredient.preferred_dimension:
                raise ValueError("Product dimension conflicts with canonical ingredient")
            key = (product.retailer_id, product.canonical_ingredient_id)
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > 8: raise ValueError("At most eight products per retailer/ingredient")

    def find(self, retailer_id): return self._retailers.get(retailer_id)

    def options(self, retailer_id, ingredient_id):
        return tuple(p for p in self._products.get((retailer_id, ingredient_id), ()) if p.availability == "available")
