from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator
from app.schemas.baskets import PantryItem, RecipeSelection, OptionalPolicy
from app.schemas.recipes import DomainModel, Unit, RecipeMatch, RecommendationResponse

Allergen = Literal["milk", "egg", "gluten", "peanut", "tree_nut", "shellfish", "fish", "soy"]
Diet = Literal["standard", "vegetarian", "vegan", "pescatarian", "gluten_free", "lactose_free"]
Goal = Literal["balanced", "high_protein", "economical", "quick", "student_friendly", "light"]

class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value):
        return value.casefold()

class PublicUser(DomainModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    created_at: datetime
    updated_at: datetime

class Preferences(DomainModel):
    dietary_pattern: Diet = "standard"
    allergies: tuple[Allergen, ...] = Field(default=(), max_length=8)
    liked_ingredients: tuple[str, ...] = Field(default=(), max_length=50)
    disliked_ingredients: tuple[str, ...] = Field(default=(), max_length=50)
    goals: tuple[Goal, ...] = Field(default=(), max_length=6)
    default_servings: int = Field(default=2, ge=1, le=12, strict=True)
    default_max_minutes: int | None = Field(default=None, ge=5, le=240, strict=True)

    @field_validator("allergies", "liked_ingredients", "disliked_ingredients", "goals")
    @classmethod
    def unique(cls, value):
        return tuple(dict.fromkeys(value))

class PantryCreate(PantryItem):
    expiration_date: date | None = None

class PantryPatch(DomainModel):
    quantity: Decimal | None = Field(default=None, ge=0, le=1000000000, max_digits=18, decimal_places=6, allow_inf_nan=False)
    unit: Unit | None = None
    expiration_date: date | None = None

class PantryView(PantryCreate):
    id: UUID
    name: str
    preparation_state: str
    created_at: datetime
    updated_at: datetime

class MealIntent(DomainModel):
    craving: str = Field(default="yemek", min_length=2, max_length=240)
    servings: int | None = Field(default=None, ge=1, le=12, strict=True)
    max_minutes: int | None = Field(default=None, ge=5, le=240, strict=True)
    dietary_pattern: Diet | None = None
    temporary_tags: tuple[Goal, ...] = Field(default=(), max_length=6)
    max_budget_try: Decimal | None = Field(default=None, gt=0, le=100000, decimal_places=2)
    allow_disliked: bool = False
    pantry_adjustments: tuple[PantryItem, ...] = Field(default=(), max_length=100)

class SavedBasketRequest(DomainModel):
    recipes: tuple[RecipeSelection, ...] = Field(min_length=1, max_length=20)
    optional_policy: OptionalPolicy = "required_only"
    pantry_adjustments: tuple[PantryItem, ...] = Field(default=(), max_length=100)


class RankingSignals(DomainModel):
    pantry_matches: int
    liked_matches: int
    goal_matches: int

class PersonalizedMatch(RecipeMatch):
    personalization_signals: RankingSignals

class PersonalizedResponse(RecommendationResponse):
    recipes: tuple[PersonalizedMatch, ...]
    conflicts: tuple[str, ...]
    profile_applied: Literal[True] = True
    applied_servings: int
    applied_max_minutes: int
