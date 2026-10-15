from decimal import Decimal, ROUND_HALF_UP, localcontext
from app.schemas.recipes import Recipe, ScaledRecipe, ScaledIngredient, UNIT_LABELS


def scale_recipe(recipe: Recipe, servings: int) -> ScaledRecipe:
    if isinstance(servings, bool) or not isinstance(servings, int) or not 1 <= servings <= 12:
        raise ValueError("servings must be an integer from 1 to 12")
    scaled = []
    with localcontext() as context:
        context.prec = 28
        for ingredient in recipe.ingredients:
            quantity = (ingredient.quantity * Decimal(servings) / Decimal(recipe.base_servings)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            display = quantity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            display_text = "<0,01" if display == 0 else format(display, "f").rstrip("0").rstrip(".").replace(".", ",")
            scaled.append(ScaledIngredient(ingredient_id=ingredient.ingredient_id, name=ingredient.name,
                quantity=quantity, display_quantity=display_text, unit=ingredient.unit, unit_label=UNIT_LABELS[ingredient.unit],
                optional=ingredient.optional, notes=ingredient.notes))
    return ScaledRecipe(recipe=recipe, requested_servings=servings, scaled_ingredients=tuple(scaled))
