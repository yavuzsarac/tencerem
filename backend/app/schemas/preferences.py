from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class MealPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    craving: str = Field(min_length=3, max_length=240)
    servings: int = Field(ge=1, le=12, strict=True)
    max_budget_try: Decimal = Field(gt=0, le=100000, max_digits=8, decimal_places=2)
    max_prep_minutes: int = Field(ge=5, le=240, strict=True)
    dietary_preference: Literal["none", "vegetarian", "vegan", "gluten_free"]

class PreferenceReceipt(BaseModel):
    mode: Literal["development"] = "development"
    message: str = "Tercihleriniz doğrulandı. Bu geliştirme sürümünde tarif oluşturulmaz ve market fiyatları sorgulanmaz."
    preferences: MealPreferences
