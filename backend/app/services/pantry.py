from dataclasses import dataclass
from decimal import Decimal
from app.repositories.ingredients import IngredientRegistry
from app.schemas.baskets import PantryItem
from app.schemas.recipes import Unit
from app.services.quantities import normalize_quantity

class BasketInputError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field

@dataclass(frozen=True)
class PantryInventory:
    quantities: dict[tuple[str, Unit], Decimal]
    unknown: frozenset[str]


def prepare_pantry(items: tuple[PantryItem, ...], registry: IngredientRegistry) -> PantryInventory:
    quantities: dict[tuple[str, Unit], Decimal] = {}
    unknown: set[str] = set()
    for index, item in enumerate(items):
        if registry.get(item.ingredient_id) is None:
            raise BasketInputError(f"pantry.{index}.ingredient_id", "Malzeme kayıtlı değil; /api/v1/ingredients listesinden bir kimlik seçin.")
        if item.quantity is None:
            if item.ingredient_id in unknown:
                raise BasketInputError(f"pantry.{index}", "Aynı malzeme için miktarı bilinmeyen stok yalnızca bir kez girilmeli.")
            unknown.add(item.ingredient_id)
            continue
        quantity, unit = normalize_quantity(item.quantity, item.unit)
        key = (item.ingredient_id, unit)
        if key in quantities:
            raise BasketInputError(f"pantry.{index}", "Aynı malzemenin uyumlu birimlerdeki stoklarını toplayıp tek satırda girin; stok iki kez sayılamaz.")
        quantities[key] = quantity
    return PantryInventory(quantities, frozenset(unknown))
