from decimal import Decimal, localcontext
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import create_app
from app.core.config import Settings
from app.repositories.catalog import RecipeCatalog, validate_catalog
from app.repositories.ingredients import IngredientRegistry
from app.schemas.recipes import Recipe, IngredientDefinition, Unit
from app.schemas.baskets import BasketRequest, PantryItem
from app.services.baskets import preview_basket
from app.services.pantry import BasketInputError
from app.services.quantities import normalize_quantity

@pytest.fixture
def catalog():
    return RecipeCatalog()

@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(Settings(_env_file=None, database_url=None)))


def make_recipe(catalog, slug, number, ingredients):
    data = catalog.recipes[0].model_dump(mode="json")
    data.update(id=f"recipe_{number}", slug=slug, name=slug.replace("-", " "), dietary_tags=[], base_servings=4)
    data["ingredients"] = [{"ingredient_id":ident, "name":catalog.registry.get(ident).name,
        "quantity":str(quantity), "unit":unit, "optional":optional} for ident,quantity,unit,optional in ingredients]
    return Recipe.model_validate(data)


def use_recipes(catalog, recipes):
    validate_catalog(tuple(recipes), catalog.registry.ingredients)
    catalog.recipes = tuple(recipes)
    catalog._by_slug = {r.slug:r for r in recipes}
    return catalog


def request_for(slugs, pantry=(), policy="required_only", servings=4):
    return BasketRequest(recipes=[{"slug":slug, "servings":servings} for slug in slugs], pantry=pantry, optional_policy=policy)


def component(basket, ingredient_id):
    return next(i for i in basket.items if i.ingredient_id == ingredient_id).components[0]

@pytest.mark.parametrize("quantity,unit,expected,canonical", [
    ("1.5", "kg", "1500", "g"), ("0.5", "l", "500", "ml"),
    ("2", "adet", "2", "adet"), ("0.25", "tbsp", "0.25", "tbsp"),
    ("1", "cup", "1", "cup"), ("3", "dessert_spoon", "3", "dessert_spoon"), ("2", "tsp", "2", "tsp")])
def test_safe_unit_normalization(quantity, unit, expected, canonical):
    assert normalize_quantity(Decimal(quantity), Unit(unit)) == (Decimal(expected), canonical)


def test_mandatory_scenario_a(catalog):
    recipe = make_recipe(catalog, "scenario-a", 900, [("chicken_breast",500,"g",False),("rice",300,"g",False),("salt",5,"g",False)])
    use_recipes(catalog,[recipe])
    request = request_for([recipe.slug],[{"ingredient_id":"chicken_breast","quantity":"300","unit":"g"},
        {"ingredient_id":"rice","quantity":"500","unit":"g"}, {"ingredient_id":"salt","quantity":None,"unit":None,"presence":True}])
    before = request.model_dump_json()
    recipe_before = recipe.model_dump_json()
    basket = preview_basket(catalog, request)
    chicken, rice, salt = (component(basket,i) for i in ["chicken_breast","rice","salt"])
    assert (chicken.required_quantity,chicken.pantry_available_quantity,chicken.pantry_allocated_quantity,chicken.missing_quantity)==(500,300,300,200)
    assert (rice.required_quantity,rice.pantry_available_quantity,rice.pantry_allocated_quantity,rice.missing_quantity)==(300,500,300,0)
    assert salt.pantry_available_quantity is None
    assert salt.pantry_allocated_quantity == 0 and salt.missing_quantity == 5 and salt.calculation_status == "presence_only"
    assert basket.summary.model_dump() == {"selected_recipe_count":1,"total_servings":4,"unique_ingredients":3,"fully_covered":1,"partially_covered":1,"items_to_buy":2,"unresolved_items":1}
    assert request.model_dump_json()==before and recipe.model_dump_json()==recipe_before
    assert basket==preview_basket(catalog,request)


def test_mandatory_scenario_b_allocate_once(catalog):
    first=make_recipe(catalog,"recipe-a",900,[("chicken_breast",300,"g",False)])
    second=make_recipe(catalog,"recipe-b",901,[("chicken_breast",300,"g",False)])
    use_recipes(catalog,[first,second])
    basket=preview_basket(catalog,request_for([first.slug,second.slug],[{"ingredient_id":"chicken_breast","quantity":"0.4","unit":"kg"}]))
    item=component(basket,"chicken_breast")
    assert (item.required_quantity,item.pantry_allocated_quantity,item.missing_quantity)==(600,400,200)
    assert [(c.slug,c.quantity,c.selection_index,c.provenance.kind) for c in item.contributions]==[("recipe-a",300,0,"curated_internal"),("recipe-b",300,1,"curated_internal")]


def test_mandatory_scenario_c_flour_mass_and_cup(catalog):
    flour=IngredientDefinition(id="wheat_flour",name="Buğday unu",aliases=("un",),category="grain",preferred_dimension="mass",default_basket_unit="g",gluten=True)
    catalog.registry=IngredientRegistry((*catalog.ingredients,flour))
    first=make_recipe(catalog,"flour-a",900,[("wheat_flour",500,"g",False)])
    second=make_recipe(catalog,"flour-b",901,[("wheat_flour",1,"cup",False)])
    use_recipes(catalog,[first,second])
    basket=preview_basket(catalog,request_for([first.slug,second.slug],[{"ingredient_id":"wheat_flour","quantity":200,"unit":"g"}]))
    item=basket.items[0]
    assert item.calculation_status=="incompatible_units" and item.warnings
    quantities={c.unit:(c.required_quantity,c.pantry_allocated_quantity,c.missing_quantity) for c in item.components}
    assert quantities=={"g":(500,200,300),"cup":(1,0,1)}
    assert basket.summary.unique_ingredients==1 and basket.summary.unresolved_items==1


def test_mass_volume_count_consolidation_and_decimal(catalog):
    first=make_recipe(catalog,"units-a",900,[("rice",500,"g",False),("water",500,"ml",False),("egg",2,"adet",False),("olive_oil","0.1","tbsp",False)])
    second=make_recipe(catalog,"units-b",901,[("rice",1,"kg",False),("water",1,"l",False),("egg",3,"adet",False),("olive_oil","0.2","tbsp",False)])
    use_recipes(catalog,[first,second])
    with localcontext() as context:
        context.prec=6
        basket=preview_basket(catalog,request_for([first.slug,second.slug]))
    for ident,expected,unit in [("rice",1500,"g"),("water",1500,"ml"),("egg",5,"adet"),("olive_oil",Decimal("0.3"),"tbsp")]:
        value=component(basket,ident)
        assert value.required_quantity==expected and value.unit==unit
        assert value.pantry_available_quantity==0 and value.missing_quantity==expected
    assert component(basket,"rice").contributions[1].source_unit=="kg"
    assert component(basket,"rice").contributions[1].source_quantity==1


def test_duplicate_selection_and_independent_scaling(catalog):
    basket=preview_basket(catalog, BasketRequest(recipes=[{"slug":"tavuklu-pilav","servings":2},{"slug":"tavuklu-pilav","servings":4}],pantry=[{"ingredient_id":"chicken_breast","quantity":400,"unit":"g"}]))
    chicken=component(basket,"chicken_breast")
    assert chicken.required_quantity==600 and chicken.missing_quantity==200
    assert [c.quantity for c in chicken.contributions]==[200,400]
    assert len(basket.selected_recipes)==2


def test_optional_policy_and_mixed_contributions(catalog):
    one=make_recipe(catalog,"optional-a",900,[("rice",100,"g",False),("yogurt",200,"g",True)])
    two=make_recipe(catalog,"optional-b",901,[("yogurt",100,"g",False)])
    use_recipes(catalog,[one,two])
    excluded=preview_basket(catalog, request_for([one.slug,two.slug]))
    assert component(excluded,"yogurt").required_quantity==100 and excluded.excluded_optional_contributions==1
    included=preview_basket(catalog, request_for([one.slug,two.slug],policy="include_optional"))
    yogurt=next(i for i in included.items if i.ingredient_id=="yogurt")
    assert yogurt.optional_status=="mixed"
    assert yogurt.components[0].required_quantity==300
    assert yogurt.components[0].mandatory_quantity==100 and yogurt.components[0].optional_quantity==200
    only=preview_basket(catalog,request_for([one.slug],policy="include_optional"))
    assert next(i for i in only.items if i.ingredient_id=="yogurt").optional_status=="optional"


def test_unknown_with_known_quantity_and_zero_stock(catalog):
    request=request_for(["tavuklu-pilav"],[{"ingredient_id":"rice","quantity":0,"unit":"g"},{"ingredient_id":"rice","presence":True}])
    rice=component(preview_basket(catalog,request),"rice")
    assert rice.pantry_available_quantity==0 and rice.pantry_allocated_quantity==0 and rice.missing_quantity==240
    assert rice.calculation_status=="presence_only"
    known=request.model_copy(update={"pantry":(PantryItem(ingredient_id="rice",quantity=100,unit="g"),PantryItem(ingredient_id="rice"))})
    rice=component(preview_basket(catalog,known),"rice")
    assert rice.pantry_allocated_quantity==100 and rice.missing_quantity==140 and rice.calculation_status=="presence_only"


def test_wrong_pantry_unit_not_consumed_and_no_cross_spoon_conversion(catalog):
    basket=preview_basket(catalog,request_for(["tavuklu-pilav"],[{"ingredient_id":"rice","quantity":1,"unit":"cup"},{"ingredient_id":"olive_oil","quantity":20,"unit":"tsp"}]))
    for ident in ["rice","olive_oil"]:
        item=next(i for i in basket.items if i.ingredient_id==ident)
        assert item.calculation_status=="incompatible_units"
        assert item.components[0].pantry_allocated_quantity==0
        assert item.components[0].missing_quantity==item.components[0].required_quantity


def test_subtraction_disabled_is_unresolved(catalog):
    definitions=tuple(i.model_copy(update={"quantity_subtraction_supported":False}) if i.id=="rice" else i for i in catalog.ingredients)
    catalog.registry=IngredientRegistry(definitions)
    basket=preview_basket(catalog,request_for(["tavuklu-pilav"],[{"ingredient_id":"rice","quantity":500,"unit":"g"}]))
    item=next(i for i in basket.items if i.ingredient_id=="rice")
    assert item.calculation_status=="unresolved"
    assert item.components[0].pantry_allocated_quantity==0 and item.components[0].missing_quantity==240

@pytest.mark.parametrize("pantry",[
    [{"ingredient_id":"rice","quantity":500,"unit":"g"},{"ingredient_id":"rice","quantity":"0.5","unit":"kg"}],
    [{"ingredient_id":"rice"},{"ingredient_id":"rice"}],
])
def test_duplicate_pantry_rejected(catalog,pantry):
    with pytest.raises(BasketInputError,match="stok|stoklarını"):
        preview_basket(catalog,request_for(["tavuklu-pilav"],pantry))

@pytest.mark.parametrize("pantry",[
    {"ingredient_id":"rice","quantity":-1,"unit":"g"},
    {"ingredient_id":"rice","quantity":"NaN","unit":"g"},
    {"ingredient_id":"rice","quantity":"Infinity","unit":"g"},
    {"ingredient_id":"rice","quantity":"0.0000001","unit":"g"},
    {"ingredient_id":"rice","quantity":1000000001,"unit":"g"},
    {"ingredient_id":"rice","quantity":1,"unit":"pinch"},
    {"ingredient_id":"rice","quantity":None,"unit":"g"},
    {"ingredient_id":"rice","quantity":1,"unit":None},
    {"ingredient_id":"rice","presence":False},
    {"ingredient_id":"rice","quantity":True,"unit":"g"},
])
def test_invalid_pantry_validation(pantry):
    with pytest.raises(ValidationError): PantryItem.model_validate(pantry)


def test_registry_aliases_and_catalog_links(catalog):
    assert {catalog.registry.resolve(v) for v in ["tavuk","TAVUK GÖĞSÜ","tavuk gogsu"]}=={"chicken_breast"}
    assert catalog.registry.resolve("tavuk suyu") is None
    assert all(catalog.registry.get(i.ingredient_id) for r in catalog.recipes for i in r.ingredients)
    assert all(i.category and i.preferred_dimension and i.default_basket_unit for i in catalog.registry.ingredients)
    wrong=catalog.ingredients[0].model_copy(update={"default_basket_unit":"ml"})
    with pytest.raises(ValueError,match="dimension"):IngredientRegistry((wrong,))


def test_basket_and_registry_endpoints(client):
    listing=client.get("/api/v1/ingredients")
    assert listing.status_code==200 and len(listing.json())==37
    response=client.post("/api/v1/baskets/preview",json={"recipes":[{"slug":"tavuklu-pilav","servings":2}],"pantry":[{"ingredient_id":"chicken_breast","quantity":"0.1","unit":"kg"}]})
    assert response.status_code==200
    data=response.json()
    assert data["mode"]=="ingredient_preview" and data["optional_policy"]=="required_only"
    chicken=next(i for i in data["items"] if i["ingredient_id"]=="chicken_breast")
    assert Decimal(chicken["components"][0]["missing_quantity"])==100
    assert data["summary"]["unique_ingredients"]==5
    assert all(i["ingredient_id"]!="yogurt" for i in data["items"])

@pytest.mark.parametrize("change",[
    {"recipes":[]}, {"recipes":[{"slug":"missing-recipe","servings":2}]},
    {"recipes":[{"slug":"tavuklu-pilav","servings":0}]},
    {"recipes":[{"slug":"tavuklu-pilav","servings":2}]*21},
    {"pantry":[{"ingredient_id":"invented_food","quantity":1,"unit":"g"}]},
    {"pantry":[{"ingredient_id":"rice"},{"ingredient_id":"rice"}]},
    {"pantry":[{"ingredient_id":"rice","quantity":1,"unit":"pinch"}]},
    {"optional_policy":"assume_all"}, {"unknown_field":True},
])
def test_invalid_basket_endpoint(client,change):
    payload={"recipes":[{"slug":"tavuklu-pilav","servings":2}]}|change
    response=client.post("/api/v1/baskets/preview",json=payload)
    assert response.status_code==422 and response.json()["error"]["fields"]
