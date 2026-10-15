from decimal import Decimal
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.core.config import Settings
from app.main import create_app
from app.repositories.catalog import RecipeCatalog, validate_catalog, DATA
from app.schemas.recipes import Recipe, RecommendationRequest, Unit
from app.services.normalization import normalize, normalize_pantry
from app.services.scaling import scale_recipe
from app.services.recommendation import recommend

@pytest.fixture(scope="module")
def catalog():
    return RecipeCatalog()

@pytest.fixture
def preferences():
    return RecommendationRequest(craving="tavuk", servings=2, max_prep_minutes=30,
        dietary_preference="none", pantry="pirinç, yoğurt")

@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(Settings(_env_file=None, database_url=None)))


def test_catalog_integrity_and_provenance(catalog):
    assert 20 <= len(catalog.recipes) <= 30
    assert len({r.id for r in catalog.recipes}) == len(catalog.recipes)
    assert len({r.slug for r in catalog.recipes}) == len(catalog.recipes)
    validate_catalog(catalog.recipes, catalog.ingredients)
    for recipe in catalog.recipes:
        assert recipe.provenance.kind == "curated_internal"
        assert recipe.provenance.author == "Tencerem development catalog"
        assert recipe.total_minutes == recipe.prep_minutes + recipe.cook_minutes
        assert recipe.instructions and recipe.ingredients
        assert all(i.quantity > 0 and i.unit in Unit for i in recipe.ingredients)

@pytest.mark.parametrize("change", [
    {"base_servings": 0}, {"prep_minutes": -1}, {"cook_minutes": -1}, {"total_minutes": 1},
    {"ingredients": []}, {"instructions": []}, {"instructions": ["  "]}, {"name": ""},
    {"provenance": {"kind": "external"}},
])
def test_recipe_validation(catalog, change):
    data = catalog.recipes[0].model_dump(mode="json")
    data.update(change)
    with pytest.raises(ValidationError):
        Recipe.model_validate(data)

@pytest.mark.parametrize("field,value", [("quantity", "0"), ("quantity", "-1"), ("quantity", "NaN"), ("unit", "pinch")])
def test_ingredient_validation(catalog, field, value):
    data = catalog.recipes[0].model_dump(mode="json")
    data["ingredients"][0][field] = value
    with pytest.raises(ValidationError): Recipe.model_validate(data)


def test_duplicate_ids_slugs_and_dietary_integrity(catalog):
    first, second, *rest = catalog.recipes
    for field in ["id", "slug"]:
        bad = second.model_copy(update={field: getattr(first, field)})
        with pytest.raises(ValueError, match="Duplicate recipe"):
            validate_catalog((first, bad, *rest), catalog.ingredients)
    bad = first.model_copy(update={"dietary_tags": ("vegetarian", "vegan")})
    with pytest.raises(ValueError, match="Contradictory"):
        validate_catalog((bad,), catalog.ingredients)


def test_malformed_data_fails_on_load(tmp_path):
    for filename in ["recipes.json", "ingredients.json"]:
        (tmp_path / filename).write_text((DATA / filename).read_text(encoding="utf-8"), encoding="utf-8")
    data = json.loads((tmp_path / "recipes.json").read_text(encoding="utf-8"))
    data[0]["ingredients"][0]["unit"] = "unknown"
    (tmp_path / "recipes.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationError): RecipeCatalog(tmp_path)

@pytest.mark.parametrize("servings,expected", [(2, "200"), (4, "400"), (6, "600")])
def test_serving_scaling_immutable(catalog, servings, expected):
    recipe = catalog.find("tavuklu-pilav")
    before = recipe.model_dump_json()
    scaled = scale_recipe(recipe, servings)
    assert scaled.scaled_ingredients[0].quantity == Decimal(expected)
    assert scaled.scaled_ingredients[0].display_quantity == expected
    assert scaled.scaled_ingredients[0].unit == "g"
    assert recipe.model_dump_json() == before
    with pytest.raises(ValidationError): recipe.base_servings = 2


def test_rounding_fractional_pieces_and_no_unit_conversion(catalog):
    recipe = catalog.find("tavuklu-pilav").model_copy(update={"base_servings": 3})
    scaled = scale_recipe(recipe, 1)
    assert scaled.scaled_ingredients[0].quantity == Decimal("133.333333")
    assert scaled.scaled_ingredients[0].display_quantity == "133,33"
    egg = scale_recipe(catalog.find("menemen"), 1).scaled_ingredients[0]
    assert egg.quantity == Decimal("1.5") and egg.display_quantity == "1,5" and egg.unit == "adet"
    assert any(i.unit == "ml" for i in scaled.scaled_ingredients)
    assert any(i.unit == "tbsp" for i in scaled.scaled_ingredients)

@pytest.mark.parametrize("servings", [0, 13, True, 2.5])
def test_invalid_scale(catalog, servings):
    with pytest.raises(ValueError): scale_recipe(catalog.recipes[0], servings)


def test_pantry_normalization(catalog):
    assert normalize("  PİRİNÇ, YoĞuRt  ") == "pirinc yogurt"
    pantry = normalize_pantry(" PİRİNÇ, pirinc, YoĞuRt, yoğurt, tavuk, tavuk göğsü, ejder meyvesi, ,", catalog.ingredients)
    assert pantry.recognized == ("rice", "yogurt", "chicken_breast")
    assert pantry.unrecognized == ("ejder meyvesi",)
    assert pantry.normalized.count("pirinc") == 1
    assert normalize_pantry("", catalog.ingredients).recognized == ()
    # Exact canonical aliases only: no substring/quantity/preparation inference.
    assert not normalize_pantry("tavuk suyu, 200 g pirinç", catalog.ingredients).recognized


def test_recommendation_manual_acceptance(catalog, preferences):
    response = recommend(catalog, preferences)
    assert response.mode == "curated" and response.budget_applied is False
    pilav = next(m for m in response.recipes if m.recipe.slug == "tavuklu-pilav")
    assert pilav.requested_servings == 2
    assert pilav.scaled_ingredients[0].quantity == 200
    assert {i.ingredient_id for i in pilav.available_ingredients} == {"rice", "yogurt"}
    assert "chicken_breast" in {i.ingredient_id for i in pilav.missing_ingredients}
    assert all(m.recipe.total_minutes <= 30 for m in response.recipes)
    assert "firinda-sebzeli-tavuk" not in {m.recipe.slug for m in response.recipes}
    for match in response.recipes:
        assert "chicken_breast" in {i.ingredient_id for i in match.recipe.ingredients}
        assert set(match.available_ingredients).isdisjoint(match.missing_ingredients)
        assert len(match.available_ingredients) + len(match.missing_ingredients) == len(match.scaled_ingredients)
        assert match.reasons and match.recipe.provenance.kind == "curated_internal"

@pytest.mark.parametrize("diet", ["vegetarian", "vegan", "gluten_free"])
def test_diet_and_time_are_hard_filters(catalog, preferences, diet):
    request = preferences.model_copy(update={"craving": "hızlı", "dietary_preference": diet, "max_prep_minutes": 25, "limit": 10})
    matches = recommend(catalog, request).recipes
    assert matches
    assert all(diet in m.recipe.dietary_tags and m.recipe.total_minutes <= 25 for m in matches)


def test_scoring_ranking_and_budget_independence(catalog, preferences):
    response = recommend(catalog, preferences)
    keys = [(-m.score, m.recipe.total_minutes, m.recipe.slug) for m in response.recipes]
    assert keys == sorted(keys)
    assert response == recommend(catalog, preferences)
    assert response == recommend(catalog, preferences.model_copy(update={"max_budget_try": Decimal("1")}))
    no_pantry = recommend(catalog, preferences.model_copy(update={"pantry": ""}))
    base = {m.recipe.id: m.score for m in no_pantry.recipes}
    for match in response.recipes:
        assert match.score == base[match.recipe.id] + 3 * len(match.available_ingredients)
    # Tavuk sote: name 10, category 6, tag 4, ingredient text 2, canonical ingredient 2.
    assert next(m.score for m in no_pantry.recipes if m.recipe.slug == "tavuk-sote") == 24

@pytest.mark.parametrize("query,slug", [("MERCİMEK", "mercimek-corbasi"), ("MAKARNA", "sebzeli-makarna"), ("corba", "mercimek-corbasi")])
def test_turkish_text_matches(catalog, preferences, query, slug):
    response = recommend(catalog, preferences.model_copy(update={"craving": query, "max_prep_minutes": 120, "limit": 10}))
    assert slug in {m.recipe.slug for m in response.recipes}


def test_no_matches_no_silent_fallback(catalog, preferences):
    for update in [{"craving": "sushi"}, {"max_prep_minutes": 5}, {"dietary_preference": "vegan"}]:
        response = recommend(catalog, preferences.model_copy(update=update))
        assert not response.recipes and "bulunamadı" in response.message


def test_list_detail_and_recommend_endpoints(client, preferences):
    recipes = client.get("/api/v1/recipes")
    assert recipes.status_code == 200 and len(recipes.json()) == 24
    detail = client.get("/api/v1/recipes/tavuklu-pilav?servings=6")
    assert detail.status_code == 200
    assert Decimal(detail.json()["scaled_ingredients"][0]["quantity"]) == 600
    assert client.get("/api/v1/recipes/tavuklu-pilav").json()["requested_servings"] == 4
    missing = client.get("/api/v1/recipes/not-a-recipe")
    assert missing.status_code == 404 and "Tarif bulunamadı" in missing.json()["error"]["message"]
    response = client.post("/api/v1/recipes/recommend", json=preferences.model_dump(mode="json"))
    assert response.status_code == 200
    assert response.json()["recognized_pantry_ids"] == ["rice", "yogurt"]
    assert response.json()["recipes"][0]["recipe"]["provenance"]["kind"] == "curated_internal"
    assert client.get("/api/v1/recipes/tavuklu-pilav?servings=0").status_code == 422

@pytest.mark.parametrize("change", [{"servings": 0}, {"servings": 1.5}, {"max_prep_minutes": 0}, {"dietary_preference": "keto"}, {"pantry": "x" * 1001}, {"limit": 11}, {"invented": True}, {"craving": "   "}])
def test_invalid_recommendation(client, preferences, change):
    payload = preferences.model_dump(mode="json") | change
    response = client.post("/api/v1/recipes/recommend", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["fields"]


def test_half_up_rounding_and_tiny_display(catalog):
    recipe = catalog.find("tavuklu-pilav")
    data = recipe.model_dump(mode="json")
    data["ingredients"][0]["quantity"] = "1.005"
    variant = Recipe.model_validate(data)
    assert scale_recipe(variant, 4).scaled_ingredients[0].display_quantity == "1,01"
    data["ingredients"][0]["quantity"] = "0.001"
    variant = Recipe.model_validate(data)
    tiny = scale_recipe(variant, 1).scaled_ingredients[0]
    assert tiny.quantity == Decimal("0.000250")
    assert tiny.display_quantity == "<0,01"


def test_unknown_ingredients_and_ambiguous_aliases_rejected(catalog):
    recipe = catalog.recipes[0]
    unknown = recipe.ingredients[0].model_copy(update={"ingredient_id": "unknown_food"})
    variant = recipe.model_copy(update={"ingredients": (unknown, *recipe.ingredients[1:])})
    with pytest.raises(ValueError, match="Unknown ingredient"):
        validate_catalog((variant,), catalog.ingredients)
    first, second, *rest = catalog.ingredients
    conflict = second.model_copy(update={"aliases": (first.name,)})
    with pytest.raises(ValueError, match="Ambiguous"):
        validate_catalog(catalog.recipes, (first, conflict, *rest))


def test_two_character_meat_query(client, preferences):
    payload = preferences.model_dump(mode="json") | {"craving": "et", "pantry": ""}
    response = client.post("/api/v1/recipes/recommend", json=payload)
    assert response.status_code == 200
    assert response.json()["recipes"]
    assert all(m["recipe"]["category"] == "Et" for m in response.json()["recipes"])
