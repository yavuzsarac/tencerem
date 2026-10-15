from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.preferences import MealPreferences

class Unit(StrEnum):
    G = "g"
    KG = "kg"
    ML = "ml"
    L = "l"
    PIECE = "adet"
    TABLESPOON = "tbsp"
    DESSERT_SPOON = "dessert_spoon"
    TEASPOON = "tsp"
    CUP = "cup"

UNIT_LABELS = {"g": "g", "kg": "kg", "ml": "ml", "l": "l", "adet": "adet",
               "tbsp": "yemek kaşığı", "dessert_spoon": "tatlı kaşığı", "tsp": "çay kaşığı", "cup": "su bardağı"}

class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

class Dimension(StrEnum):
    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"
    CULINARY = "culinary"

class IngredientDefinition(DomainModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    name: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    category: Literal["meat", "poultry", "fish", "dairy", "grain", "pasta", "legume", "vegetable", "fruit", "oil", "spice", "condiment", "bakery", "egg", "other"]
    preferred_dimension: Dimension
    default_basket_unit: Unit
    quantity_subtraction_supported: bool = True
    preparation_state: Literal["raw", "dry", "cooked", "ready_to_use"] = "ready_to_use"
    allergens: tuple[Literal["milk", "egg", "gluten", "peanut", "tree_nut", "shellfish", "fish", "soy"], ...] = ()
    allergen_metadata_complete: bool = False
    animal: bool = False
    meat: bool = False
    gluten: bool = False

    @model_validator(mode="after")
    def allergen_consistency(self):
        if self.allergen_metadata_complete:
            if self.gluten and "gluten" not in self.allergens:
                raise ValueError("Reviewed gluten ingredient must declare gluten allergen")
            if self.category == "dairy" and "milk" not in self.allergens:
                raise ValueError("Reviewed dairy ingredient must declare milk allergen")
            if self.category == "egg" and "egg" not in self.allergens:
                raise ValueError("Reviewed egg ingredient must declare egg allergen")
        return self

class Ingredient(DomainModel):
    ingredient_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    name: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0, le=100000, allow_inf_nan=False, decimal_places=3)
    unit: Unit
    optional: bool = False
    notes: str | None = None

class Provenance(DomainModel):
    kind: Literal["curated_internal"] = "curated_internal"
    author: Literal["Tencerem development catalog"] = "Tencerem development catalog"
    version: Literal["1"] = "1"
    note: str = "Yerel geliştirme tarifi; harici kaynaktan alınmadı, profesyonel mutfak testi yapılmadı."

class Recipe(DomainModel):
    id: str = Field(pattern=r"^recipe_[0-9]{3}$")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    cuisine: str = Field(min_length=2)
    category: str = Field(min_length=2)
    tags: tuple[str, ...] = Field(min_length=1)
    dietary_tags: tuple[Literal["vegetarian", "vegan", "gluten_free"], ...] = ()
    prep_minutes: int = Field(ge=1, le=240, strict=True)
    cook_minutes: int = Field(ge=0, le=240, strict=True)
    total_minutes: int = Field(ge=1, le=480, strict=True)
    difficulty: Literal["easy", "medium"]
    base_servings: int = Field(ge=1, le=12, strict=True)
    ingredients: tuple[Ingredient, ...] = Field(min_length=1)
    instructions: tuple[str, ...] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def integrity(self) -> Self:
        if self.total_minutes != self.prep_minutes + self.cook_minutes:
            raise ValueError("total_minutes must equal prep_minutes + cook_minutes")
        if any(not step.strip() for step in self.instructions):
            raise ValueError("instructions must not be blank")
        ids = [i.ingredient_id for i in self.ingredients]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate ingredient in recipe")
        if "vegan" in self.dietary_tags and "vegetarian" not in self.dietary_tags:
            raise ValueError("vegan recipes must also be tagged vegetarian")
        return self

class RecommendationRequest(MealPreferences):
    craving: str = Field(min_length=2, max_length=240)
    # Budget is optional here and is explicitly not used until real basket data exists.
    max_budget_try: Decimal | None = Field(default=None, gt=0, le=100000, max_digits=8, decimal_places=2)
    pantry: str = Field(default="", max_length=1000)
    limit: int = Field(default=5, ge=1, le=10, strict=True)

class ScaledIngredient(DomainModel):
    ingredient_id: str
    name: str
    quantity: Decimal
    display_quantity: str
    unit: Unit
    unit_label: str
    optional: bool
    notes: str | None

class ScaledRecipe(DomainModel):
    recipe: Recipe
    requested_servings: int
    scaled_ingredients: tuple[ScaledIngredient, ...]

class RecipeMatch(ScaledRecipe):
    available_ingredients: tuple[ScaledIngredient, ...]
    missing_ingredients: tuple[ScaledIngredient, ...]
    score: int
    reasons: tuple[str, ...]

class RecommendationResponse(DomainModel):
    mode: Literal["curated"] = "curated"
    requested_servings: int
    recipes: tuple[RecipeMatch, ...]
    normalized_pantry: tuple[str, ...]
    recognized_pantry_ids: tuple[str, ...]
    unrecognized_pantry: tuple[str, ...]
    message: str
    budget_applied: Literal[False] = False
    warnings: tuple[str, ...] = (
        "Bütçe sıralamada kullanılmaz; market fiyatı hesaplanmaz.",
        "Evde var eşleşmesi miktar yeterliliğini doğrulamaz. Hesaplanan ihtiyaç için sepet önizlemesini inceleyin.",
        "Beslenme etiketleri içerik temellidir; alerjen ve çapraz bulaşma güvencesi değildir.",
    )
