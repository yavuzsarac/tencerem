from decimal import Decimal
from typing import Literal, Self
from pydantic import Field, model_validator
from app.schemas.recipes import DomainModel, Unit, Provenance

OptionalPolicy = Literal["required_only", "include_optional"]
CalculationStatus = Literal["exact", "presence_only", "incompatible_units", "unresolved"]

class RecipeSelection(DomainModel):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    servings: int = Field(ge=1, le=12, strict=True)

class PantryItem(DomainModel):
    ingredient_id: str = Field(min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]+$")
    quantity: Decimal | None = Field(default=None, ge=0, le=1000000000, max_digits=18, decimal_places=6, allow_inf_nan=False)
    unit: Unit | None = None
    presence: Literal[True] = True

    @model_validator(mode="after")
    def paired_quantity(self) -> Self:
        if (self.quantity is None) != (self.unit is None):
            raise ValueError("quantity ve unit birlikte verilmeli; miktar bilinmiyorsa ikisi de null olmalı")
        return self

class BasketRequest(DomainModel):
    recipes: tuple[RecipeSelection, ...] = Field(min_length=1, max_length=20)
    pantry: tuple[PantryItem, ...] = Field(default=(), max_length=200)
    optional_policy: OptionalPolicy = "required_only"

class SelectedRecipe(RecipeSelection):
    selection_index: int
    recipe_id: str
    name: str
    provenance: Provenance

class RecipeContribution(DomainModel):
    selection_index: int
    recipe_id: str
    slug: str
    name: str
    servings: int
    quantity: Decimal
    unit: Unit
    quantity_display: str
    source_quantity: Decimal
    source_unit: Unit
    optional: bool
    notes: str | None
    provenance: Provenance

class PantryStock(DomainModel):
    quantity: Decimal | None
    unit: Unit | None
    display: str

class QuantityComponent(DomainModel):
    unit: Unit
    unit_label: str
    required_quantity: Decimal
    mandatory_quantity: Decimal
    optional_quantity: Decimal
    pantry_available_quantity: Decimal | None
    pantry_allocated_quantity: Decimal
    missing_quantity: Decimal
    calculation_status: CalculationStatus
    contributions: tuple[RecipeContribution, ...]
    required_display: str
    available_display: str
    allocated_display: str
    missing_display: str
    explanation: str

class BasketItem(DomainModel):
    ingredient_id: str
    name: str
    category: str
    components: tuple[QuantityComponent, ...]
    pantry_stock: tuple[PantryStock, ...]
    unknown_pantry_quantity: bool
    optional_status: Literal["required", "optional", "mixed"]
    calculation_status: CalculationStatus
    warnings: tuple[str, ...]

class BasketSummary(DomainModel):
    selected_recipe_count: int
    total_servings: int
    unique_ingredients: int
    fully_covered: int
    partially_covered: int
    items_to_buy: int
    unresolved_items: int

class BasketPreview(DomainModel):
    mode: Literal["ingredient_preview"] = "ingredient_preview"
    items: tuple[BasketItem, ...]
    selected_recipes: tuple[SelectedRecipe, ...]
    optional_policy: OptionalPolicy
    excluded_optional_contributions: int
    summary: BasketSummary
    warnings: tuple[str, ...] = (
        "Bu bir malzeme sepeti önizlemesidir; fiyat, market ürünü ve sipariş içermez.",
        "Önizleme evdeki stoğu değiştirmez. Miktarı bilinmeyen stok ihtiyaçtan düşülmez.",
        "Kaşık/bardak, kütle ve hacim arasında tahmini dönüşüm yapılmaz. Hazırlık durumunu ve tarif notlarını kontrol edin.",
    )
