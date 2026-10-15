from decimal import Decimal, localcontext
from itertools import product as combinations
import json
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings
from app.repositories.catalog import RecipeCatalog
from app.repositories.markets import MarketCatalog
from app.schemas.markets import Product, Retailer
from app.schemas.baskets import BasketRequest
from app.services.baskets import preview_basket
from app.services.pricing import optimize_packages, price_basket, compare_basket, OptimizationLimit
from test_baskets import make_recipe, use_recipes, request_for
from test_accounts import app, client, register, save


@pytest.fixture
def catalog(): return RecipeCatalog()


def package(ident="rice", size="1000", price="60.00", unit="g", key="product-a", retailer="demo-a", **extra):
    return Product.model_validate({"id":key,"retailer_id":retailer,"name":"Demo ürün", "brand":"Demo",
        "canonical_ingredient_id":ident,"package_quantity":size,"package_unit":unit,"price":price,
        "observed_at":"2026-10-01T00:00:00Z",**extra})


def markets(catalog, products):
    return MarketCatalog(catalog.registry, retailers=(Retailer(id="demo-a",slug="market-a",name="Market A · Demo"),
        Retailer(id="demo-b",slug="market-b",name="Market B · Demo")),products=products)


def basket_for(catalog, ingredients, pantry=(), policy="required_only"):
    recipe=make_recipe(catalog,"pricing-test",900,ingredients)
    use_recipes(catalog,[recipe])
    return preview_basket(catalog,request_for([recipe.slug],pantry,policy))


@pytest.mark.parametrize("ident,needed,size,unit,price,count,bought,surplus,total",[
    ("rice","700","1","kg","60.00",1,"1000","300","60.00"),
    ("chicken_breast","1200","500","g","90.00",3,"1500","300","270.00"),
    ("milk","1500","1","l","30.00",2,"2000","500","60.00"),
    ("egg","7","6","adet","36.00",2,"12","5","72.00"),
    ("rice","1000","1000","g","60.00",1,"1000","0","60.00"),
    ("rice","1000.000001","1000","g","60.00",2,"2000","999.999999","120.00"),
    ("rice","0.000001","1000","g","0.10",1,"1000","999.999999","0.10")])
def test_packages_mass_volume_count_and_boundaries(ident,needed,size,unit,price,count,bought,surplus,total):
    canonical="ml" if unit=="l" else unit if unit=="adet" else "g"
    purchases,purchased,left,cost=optimize_packages(Decimal(needed),canonical,[package(ident,size,price,unit)])
    assert purchases[0].package_count==count
    assert (purchased,left,cost)==tuple(map(Decimal,(bought,surplus,total)))
    assert purchases[0].model_dump(mode="json")["line_total"]==total


@pytest.mark.parametrize("needed,small,large,cost,counts",[
    ("700","50.00","80.00","80.00",(0,1)),
    ("900","30.00","70.00","60.00",(2,0)),
    ("1400","35.00","60.00","95.00",(1,1))])
def test_lowest_total_cost_and_mixed_packages(needed,small,large,cost,counts):
    options=(package(size="500",price=small,key="small"),package(size="1000",price=large,key="large"))
    purchases,_,_,total=optimize_packages(Decimal(needed),"g",options)
    found={p.product.id:p.package_count for p in purchases}
    assert total==Decimal(cost)
    assert (found.get("small",0),found.get("large",0))==counts


def test_ties_surplus_then_package_count_then_stable_id():
    a=package(size="500",price="30",key="a")
    b=package(size="1000",price="60",key="b")
    c=package(size="1200",price="60",key="c")
    purchases,bought,_,_=optimize_packages(Decimal(900),"g",[c,a,b])
    assert bought==1000 and [(p.product.id,p.package_count) for p in purchases]==[("b",1)]
    duplicate=b.model_copy(update={"id":"z"})
    assert optimize_packages(Decimal(900),"g",[duplicate,b])[0][0].product.id=="b"


def test_optimizer_matches_independent_small_exhaustive_search():
    options=(package(size="3",price="0.11",key="a"),package(size="5",price="0.17",key="b"),package(size="7",price="0.25",key="c"))
    for needed in range(1,25):
        possibilities=[]
        for counts in combinations(range(10),repeat=3):
            bought=sum(int(p.package_quantity)*n for p,n in zip(options,counts))
            if bought<needed:continue
            cost=sum((p.price*n for p,n in zip(options,counts)),Decimal(0))
            possibilities.append((cost,bought-needed,sum(counts),tuple(-n for n in counts)))
        expected=min(possibilities)
        purchases,_,surplus,cost=optimize_packages(Decimal(needed),"g",options)
        counts={p.product.id:p.package_count for p in purchases}
        assert (cost,surplus,sum(counts.values()),tuple(-counts.get(p.id,0) for p in options))==expected


def test_exact_money_and_context_isolation():
    with localcontext() as context:
        context.prec=4
        result=optimize_packages(Decimal(3),"g",[package(size="1",price="0.10")])
    assert result[3]==Decimal("0.30") and result[0][0].model_dump(mode="json")["line_total"]=="0.30"


def test_pantry_subtraction_before_pricing(catalog):
    basket=basket_for(catalog,[("chicken_breast",500,"g",False)],
        [{"ingredient_id":"chicken_breast","quantity":"300","unit":"g"}])
    market=markets(catalog,[package("chicken_breast","500","90")])
    before=basket.model_dump_json()
    estimate=price_basket(basket,market,market.find("demo-a"))
    line=estimate.items[0]
    assert (line.required_missing_quantity,line.package_count,line.purchased_quantity,line.surplus_quantity,line.line_total)==(200,1,500,300,90)
    assert basket.model_dump_json()==before


def test_multi_recipe_consolidation_before_pricing(catalog):
    a=make_recipe(catalog,"pricing-a",900,[("chicken_breast",300,"g",False)])
    b=make_recipe(catalog,"pricing-b",901,[("chicken_breast",400,"g",False)])
    use_recipes(catalog,[a,b])
    request=request_for([a.slug,b.slug],[{"ingredient_id":"chicken_breast","quantity":200,"unit":"g"}])
    before=request.model_dump_json()
    basket=preview_basket(catalog,request)
    market=markets(catalog,[package("chicken_breast","500","90")])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert len(estimate.items)==1 and estimate.items[0].required_missing_quantity==500
    assert estimate.items[0].package_count==1 and estimate.basket_total==90
    assert request.model_dump_json()==before and len(basket.items[0].components[0].contributions)==2


@pytest.mark.parametrize("policy,complete,optional",[("required_only",True,False),("include_optional",False,True)])
def test_optional_ingredients_not_silently_mandatory(catalog,policy,complete,optional):
    basket=basket_for(catalog,[("rice",700,"g",False),("yogurt",100,"g",True)],policy=policy)
    market=markets(catalog,[package()])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert estimate.complete==complete
    assert any(i.optional_status=="optional" for i in estimate.items)==optional


def test_missing_products_not_zero_fulfillment(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False),("yogurt",100,"g",False)])
    market=markets(catalog,[package()])
    estimate=price_basket(basket,market,market.find("demo-a"))
    line=next(i for i in estimate.items if i.ingredient_id=="yogurt")
    assert not estimate.complete and estimate.basket_total is None
    assert (estimate.total_required_ingredients,estimate.fulfilled_count,estimate.unavailable_count)==(2,1,1)
    assert line.status=="unavailable" and line.line_total is None and line.purchased_quantity is None and not line.purchases


def test_partial_cheaper_never_beats_complete(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False),("yogurt",100,"g",False)])
    market=markets(catalog,[package(price="100"),package(price="100",key="rice-b",retailer="demo-b"),
        package("yogurt","500","40",key="yogurt-b",retailer="demo-b")])
    comparison=compare_basket(basket,market)
    assert comparison.recommended_retailer_id=="demo-b"
    assert comparison.estimates[0].basket_total==140 and comparison.estimates[1].priced_subtotal==100


def test_complete_markets_compare_cost(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False)])
    market=markets(catalog,[package(price="180"),package(price="160",key="rice-b",retailer="demo-b")])
    comparison=compare_basket(basket,market)
    assert comparison.recommended_retailer_id=="demo-b" and comparison.estimates[0].basket_total==160


def test_no_complete_market_has_no_cheapest_claim(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False),("yogurt",100,"g",False)])
    market=markets(catalog,[package(price="100"),package(price="50",key="rice-b",retailer="demo-b")])
    comparison=compare_basket(basket,market)
    assert comparison.recommended_retailer_id is None
    assert all(e.basket_total is None for e in comparison.estimates)
    # Equal partial coverage ties by ID, not misleading omitted-item subtotal.
    assert comparison.estimates[0].retailer.id=="demo-a"


def test_unavailable_product_excluded_and_empty_pantry_basket(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False)])
    market=markets(catalog,[package(availability="unavailable")])
    assert price_basket(basket,market,market.find("demo-a")).items[0].status=="unavailable"
    basket=basket_for(catalog,[("rice",700,"g",False)],[{"ingredient_id":"rice","quantity":"1","unit":"kg"}])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert estimate.complete and estimate.basket_total==0 and not estimate.items
    assert compare_basket(basket,market).recommended_retailer_id is None


@pytest.mark.parametrize("ident,unit,package_unit",[("olive_oil","tbsp","ml"),("rice","cup","g"),("milk","g","ml")])
def test_no_density_or_culinary_conversion(catalog,ident,unit,package_unit):
    basket=basket_for(catalog,[(ident,1,unit,False)])
    market=markets(catalog,[package(ident,unit=package_unit)])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert estimate.items[0].status=="incompatible_unit" and not estimate.complete and estimate.basket_total is None


def test_component_coverage_counted_per_ingredient(catalog):
    a=make_recipe(catalog,"pricing-a",900,[("rice",700,"g",False)])
    b=make_recipe(catalog,"pricing-b",901,[("rice",1,"cup",False)])
    use_recipes(catalog,[a,b])
    basket=preview_basket(catalog,request_for([a.slug,b.slug]))
    market=markets(catalog,[package()])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert len(estimate.items)==2 and estimate.fulfilled_count==0 and estimate.unavailable_count==1
    assert estimate.basket_total is None and estimate.priced_subtotal==60


def test_unknown_pantry_quantity_priced_conservatively(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False)],[{"ingredient_id":"rice"}])
    market=markets(catalog,[package()])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert estimate.items[0].required_missing_quantity==700 and estimate.items[0].calculation_status=="presence_only"


def test_disabled_subtraction_remains_unresolved(catalog):
    from app.repositories.ingredients import IngredientRegistry
    registry=tuple(i.model_copy(update={"quantity_subtraction_supported":False}) if i.id=="rice" else i for i in catalog.ingredients)
    catalog.registry=IngredientRegistry(registry)
    basket=basket_for(catalog,[("rice",700,"g",False)])
    market=markets(catalog,[package()])
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert estimate.items[0].status=="unresolved" and estimate.basket_total is None


def test_search_limit_explicit_not_approximate(catalog):
    options=[package(size="1",key="one"),package(size="1.000001",key="two")]
    with pytest.raises(OptimizationLimit):optimize_packages(Decimal(700),"g",options)
    basket=basket_for(catalog,[("rice",700,"g",False)])
    market=markets(catalog,options)
    estimate=price_basket(basket,market,market.find("demo-a"))
    assert estimate.items[0].status=="optimization_limit" and estimate.basket_total is None


def test_inactive_markets_are_not_recommended(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False)])
    inactive=Retailer(id="demo-a",slug="market-a",name="Market A",active=False)
    market=MarketCatalog(catalog.registry,retailers=(inactive,),products=(package(),))
    compared=compare_basket(basket,market)
    assert not compared.estimates and compared.recommended_retailer_id is None
    assert "alışveriş gerekmiyor" not in compared.message


def test_complete_tie_is_stable_and_inactive_api_returns_404(catalog):
    basket=basket_for(catalog,[("rice",700,"g",False)])
    market=markets(catalog,[package(),package(key="rice-b",retailer="demo-b")])
    assert compare_basket(basket,market).recommended_retailer_id=="demo-a"
    app=create_app(Settings(_env_file=None))
    inactive=Retailer(id="demo-a",slug="market-a",name="Market A",active=False)
    app.state.markets=MarketCatalog(catalog.registry,retailers=(inactive,),products=(package(),))
    with TestClient(app) as c:
        assert c.get("/api/v1/markets").json()==[]
        assert c.get("/api/v1/markets/demo-a/products").status_code==404


@pytest.mark.parametrize("missing", [Decimal(0),Decimal(-1),Decimal("NaN"),0.1])
def test_optimizer_rejects_invalid_or_float_requirements(missing):
    with pytest.raises(ValueError):optimize_packages(missing,"g",[package()])


def test_catalog_invalid_file_fails_loading_loudly(catalog,tmp_path):
    path=tmp_path/"invalid-market.json"
    path.write_text(json.dumps({"retailers":[Retailer(id="demo-a",slug="market-a",name="Market A").model_dump()],
        "products":[package().model_dump(mode="json"),package().model_dump(mode="json")]}),encoding="utf-8")
    with pytest.raises(ValueError,match="Duplicate product"):
        MarketCatalog(catalog.registry,path=path)


@pytest.mark.parametrize("patch",[
    {"price":"0"},{"price":"-1"},{"price":"0.001"},{"price":0.1},{"price":"NaN"},
    {"package_quantity":"0"},{"package_quantity":"-1"},{"package_quantity":0.1},
    {"package_unit":"cup"},{"package_unit":"oz"},{"currency":"USD"},{"availability":"maybe"},
    {"observed_at":"2026-10-01T00:00:00"},{"source":"live"},
    {"package_unit":"adet","package_quantity":"0.5"}])
def test_product_schema_rejects_invalid_data(patch):
    body=package().model_dump(mode="json");body.update(patch)
    with pytest.raises(ValidationError):Product.model_validate(body)


@pytest.mark.parametrize("case",["duplicate_product","orphan","wrong_retailer","dimension","duplicate_retailer","duplicate_slug","too_many"])
def test_market_catalog_integrity(catalog,case):
    p=package()
    retailers=(Retailer(id="demo-a",slug="market-a",name="Market A"),)
    products=[p]
    if case=="duplicate_product":products=[p,p]
    if case=="orphan":products=[p.model_copy(update={"canonical_ingredient_id":"orphan"})]
    if case=="wrong_retailer":products=[p.model_copy(update={"retailer_id":"unknown"})]
    if case=="dimension":products=[p.model_copy(update={"canonical_ingredient_id":"milk"})]
    if case=="duplicate_retailer":retailers=(retailers[0],retailers[0])
    if case=="duplicate_slug":retailers=(*retailers,retailers[0].model_copy(update={"id":"other"}))
    if case=="too_many":products=[p.model_copy(update={"id":f"p-{i}"}) for i in range(9)]
    with pytest.raises(ValueError):MarketCatalog(catalog.registry,retailers=retailers,products=products)


def test_startup_and_data_provenance(catalog):
    application=create_app(Settings(_env_file=None))
    market=application.state.markets
    assert len(market.retailers)==2 and len(market.products)==65
    assert all(p.source=="curated_demo" and p.currency=="TRY" for p in market.products)
    assert any(p.availability=="unavailable" for p in market.products)
    assert {p.canonical_ingredient_id for p in market.products}<={i.id for i in catalog.ingredients}


def test_apis_no_ai_no_db_no_trusted_client_totals():
    application=create_app(Settings(_env_file=None))
    class ForbiddenAI:
        def __getattr__(self,name):raise AssertionError("Pricing must never call AI")
    application.state.ai_provider=ForbiddenAI()
    body={"recipes":[{"slug":"tavuklu-pilav","servings":5}],"pantry":[
        {"ingredient_id":"chicken_breast","quantity":"300","unit":"g"},
        {"ingredient_id":"salt","quantity":"10","unit":"tsp"},
        {"ingredient_id":"olive_oil","quantity":"10","unit":"tbsp"}]}
    with TestClient(application) as c:
        assert len(c.get("/api/v1/markets").json())==2
        assert c.get("/api/v1/markets/demo-a/products").json()[0]["source"]=="curated_demo"
        assert c.get("/api/v1/markets/missing/products").status_code==404
        response=c.post("/api/v1/baskets/compare",json=body)
        assert response.status_code==200,response.text
        assert response.headers["cache-control"]=="no-store"
        data=response.json()
        assert data["mode"]=="demo_market_comparison" and "canlı fiyat değildir" in data["notice"]
        assert data["recommended_retailer_id"] is not None
        assert all(e["complete"] and isinstance(e["basket_total"],str) for e in data["estimates"])
        estimate=c.post("/api/v1/baskets/price",json={**body,"retailer_id":"demo-a"}).json()["estimate"]
        assert next(i for i in estimate["items"] if i["ingredient_id"]=="chicken_breast")["required_missing_quantity"]=="200.000000"
        assert c.post("/api/v1/baskets/price",json={**body,"retailer_id":"missing"}).status_code==404
        assert c.post("/api/v1/baskets/compare",json={**body,"subtotal":"1.00"}).status_code==422
        assert c.post("/api/v1/baskets/compare",json={"recipes":[{"slug":"invalid","servings":2}]}).status_code==422


def test_saved_pantry_prices_scope_and_constraints(client,app):
    register(client)
    for ident,quantity in (("chicken_breast","300"),("rice","500")):
        assert client.post("/api/v1/me/pantry",json={"ingredient_id":ident,"quantity":quantity,"unit":"g"}).status_code==201
    body={"recipes":[{"slug":"tavuklu-pilav","servings":5}]}
    response=client.post("/api/v1/me/baskets/compare",json=body)
    assert response.status_code==200,response.text
    estimate=response.json()["estimates"][0]
    assert next(i for i in estimate["items"] if i["ingredient_id"]=="chicken_breast")["required_missing_quantity"]=="200.000000"
    assert all(i["ingredient_id"]!="rice" for i in estimate["items"])
    assert client.post("/api/v1/me/baskets/price",json={**body,"retailer_id":"demo-a"}).status_code==200
    save(client,dietary_pattern="vegetarian")
    assert client.post("/api/v1/me/baskets/compare",json=body).status_code==422
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/me/baskets/compare",json=body).status_code==401
    register(client,"other-pricing@example.com")
    response=client.post("/api/v1/me/baskets/compare",json=body)
    estimate=response.json()["estimates"][0]
    assert next(i for i in estimate["items"] if i["ingredient_id"]=="chicken_breast")["required_missing_quantity"]=="500.000000"
    assert client.post("/api/v1/me/baskets/compare",json={**body,"user_id":"other"}).status_code==422
