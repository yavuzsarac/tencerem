import json
from pathlib import Path
from app.schemas.recipes import IngredientDefinition, Recipe
from app.repositories.ingredients import IngredientRegistry

DATA = Path(__file__).resolve().parents[1] / "data"


def validate_catalog(recipes: tuple[Recipe, ...], ingredients: tuple[IngredientDefinition, ...]) -> None:
    if not recipes or not ingredients:
        raise ValueError("Catalog must not be empty")
    for attribute in ("id", "slug"):
        values = [getattr(r, attribute) for r in recipes]
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate recipe {attribute}")
    registry = IngredientRegistry(ingredients)
    definitions = {i.id: i for i in registry.ingredients}
    for recipe in recipes:
        for item in recipe.ingredients:
            if item.ingredient_id not in definitions:
                raise ValueError(f"Unknown ingredient: {item.ingredient_id}")
            definition = definitions[item.ingredient_id]
            if item.name != definition.name:
                raise ValueError("Ingredient display name differs from canonical definition")
            diets = recipe.dietary_tags
            if ("vegan" in diets and definition.animal) or ("vegetarian" in diets and definition.meat) or ("gluten_free" in diets and definition.gluten):
                raise ValueError(f"Contradictory dietary tag: {recipe.slug}")

class RecipeCatalog:
    def __init__(self, data_dir: Path = DATA):
        self.ingredients = tuple(IngredientDefinition.model_validate(i) for i in json.loads((data_dir / "ingredients.json").read_text(encoding="utf-8")))
        self.recipes = tuple(Recipe.model_validate(r) for r in json.loads((data_dir / "recipes.json").read_text(encoding="utf-8")))
        validate_catalog(self.recipes, self.ingredients)
        self.registry = IngredientRegistry(self.ingredients)
        self._by_slug = {r.slug: r for r in self.recipes}

    def find(self, slug: str) -> Recipe | None:
        return self._by_slug.get(slug)
