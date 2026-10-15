from app.schemas.recipes import IngredientDefinition
from app.services.normalization import normalize
from app.services.quantities import dimension

class IngredientRegistry:
    def __init__(self, ingredients: tuple[IngredientDefinition, ...]):
        self.ingredients = ingredients
        self._by_id = {i.id: i for i in ingredients}
        self._aliases: dict[str, str] = {}
        if len(self._by_id) != len(ingredients):
            raise ValueError("Duplicate ingredient ID")
        for ingredient in ingredients:
            if dimension(ingredient.default_basket_unit) != ingredient.preferred_dimension:
                raise ValueError("Default basket unit must match preferred dimension")
            for alias in (ingredient.id.replace("_", " "), ingredient.name, *ingredient.aliases):
                key = normalize(alias)
                if not key or (key in self._aliases and self._aliases[key] != ingredient.id):
                    raise ValueError(f"Ambiguous ingredient alias: {key}")
                self._aliases[key] = ingredient.id

    def get(self, ingredient_id: str) -> IngredientDefinition | None:
        return self._by_id.get(ingredient_id)

    def resolve(self, name: str) -> str | None:
        return self._aliases.get(normalize(name))
