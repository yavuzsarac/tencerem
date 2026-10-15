from typing import Literal, Annotated
from pydantic import Field
from app.schemas.recipes import DomainModel
from app.schemas.users import Diet, Goal, MealIntent, PersonalizedResponse
IngredientName = Annotated[str, Field(min_length=1, max_length=80)]


class ParsedIntent(DomainModel):
    """Untrusted provider patch; names are resolved through the registry afterwards."""
    in_scope: bool = True
    servings: int | None = Field(default=None, ge=1, le=12, strict=True)
    max_minutes: int | None = Field(default=None, ge=5, le=240, strict=True)
    dietary_pattern: Diet | None = None
    goals: tuple[Goal, ...] = Field(default=(), max_length=6)
    include_ingredients: tuple[IngredientName, ...] = Field(default=(), max_length=20)
    exclude_ingredients: tuple[IngredientName, ...] = Field(default=(), max_length=20)
    pantry_ingredients: tuple[IngredientName, ...] = Field(default=(), max_length=20)
    unsupported_constraints: tuple[Annotated[str, Field(max_length=160)], ...] = Field(default=(), max_length=5)


class Decision(DomainModel):
    slug: str = Field(min_length=1, max_length=100)
    # Never accept model prose as factual explanation. Render verified fact codes.
    reason_codes: tuple[Literal["time", "pantry", "goals", "likes"], ...] = Field(default=(), max_length=4)


class SessionIntent(DomainModel):
    meal: MealIntent = MealIntent()
    include_ids: tuple[IngredientName, ...] = Field(default=(), max_length=20)
    exclude_ids: tuple[IngredientName, ...] = Field(default=(), max_length=20)
    pantry_ids: tuple[IngredientName, ...] = Field(default=(), max_length=20)


class AssistantRequest(DomainModel):
    text: str = Field(min_length=2, max_length=500)
    previous_intent: SessionIntent | None = None
    controls: MealIntent = MealIntent()
    pantry: str = Field(default="", max_length=1000)
    shown_slugs: tuple[Annotated[str, Field(min_length=1, max_length=100)], ...] = Field(default=(), max_length=24)
    current_slug: str | None = Field(default=None, max_length=100)


class AssistantRecommendations(PersonalizedResponse):
    profile_applied: bool


class AssistantResponse(DomainModel):
    intent: SessionIntent
    recommendations: AssistantRecommendations
    engine: Literal["ai_assisted", "deterministic_fallback"]
    notices: tuple[str, ...]
    selected_slug: str | None
    reason: str | None
    matched_needs: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    understood: tuple[str, ...]
