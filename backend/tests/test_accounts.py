from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import io
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, inspect
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.main import create_app
from app.core.config import Settings
from app.models.users import User, AuthSession, now_utc
from app.services.auth import COOKIE, verify_password, token_digest
from app.schemas.users import Preferences, MealIntent
from app.schemas.recipes import IngredientDefinition
from app.services.personalization import personalized_recommend

HEADERS={"Origin":"http://localhost:3000","X-Tencerem-CSRF":"1"}
PASSWORD="a-long-test-password-42"
ROOT=Path(__file__).resolve().parents[1]

def migrate(engine, action="upgrade", revision="head"):
    config=Config(str(ROOT/"alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"]=connection
        getattr(command,action)(config,revision)

@pytest.fixture
def app(tmp_path):
    settings=Settings(_env_file=None,database_url=f"sqlite:///{(tmp_path/'isolated.sqlite').as_posix()}",
        environment="test",allow_test_sqlite=True,auth_secret="isolated-test-secret-never-for-production",cookie_secure=False)
    application=create_app(settings)
    migrate(application.state.engine)
    yield application
    application.state.engine.dispose()

@pytest.fixture
def client(app):
    with TestClient(app) as c:
        c.headers.update(HEADERS)
        yield c


def register(client,email="user@example.com"):
    response=client.post("/api/v1/auth/register",json={"email":email,"password":PASSWORD})
    assert response.status_code==201,response.text
    return response.json()


def save(client,**fields):
    response=client.put("/api/v1/me/preferences",json=fields)
    assert response.status_code==200,response.text
    return response.json()


def test_migrations_upgrade_downgrade_reupgrade(app):
    engine=app.state.engine
    assert set(inspect(engine).get_table_names())=={"alembic_version","users","user_preferences","auth_sessions","pantry_entries"}
    migrate(engine,"current",None)
    migrate(engine,"downgrade","base")
    assert inspect(engine).get_table_names()==["alembic_version"]
    migrate(engine)
    assert "users" in inspect(engine).get_table_names()


def test_postgres_offline_migration_sql():
    output=io.StringIO();config=Config(str(ROOT/"alembic.ini"),output_buffer=output)
    command.upgrade(config,"head",sql=True)
    sql=output.getvalue()
    assert "TIMESTAMP WITH TIME ZONE" in sql and "NUMERIC(18, 6)" in sql and "CREATE TABLE users" in sql


def test_registration_hashing_duplicate_logout_expiration(client,app):
    user=register(client,"User@Example.com")
    assert user["email"]=="user@example.com" and "password_hash" not in user
    token=client.cookies.get(COOKIE)
    assert token and "httponly" in client.post("/api/v1/auth/login",json={"email":"USER@example.com","password":PASSWORD}).headers["set-cookie"].lower()
    with Session(app.state.engine) as db:
        record=db.scalar(select(User))
        assert record.password_hash.startswith("$argon2id$") and PASSWORD not in record.password_hash
        assert verify_password(record.password_hash,PASSWORD) and not verify_password(record.password_hash,"wrong")
        assert db.get(AuthSession,token_digest(token,app.state.settings)) is None  # rotated on login
    duplicate=client.post("/api/v1/auth/register",json={"email":"USER@example.com","password":PASSWORD})
    assert duplicate.status_code==409
    assert client.get("/api/v1/me").json()["id"]==user["id"]
    token=client.cookies.get(COOKIE)
    assert client.post("/api/v1/auth/logout").status_code==204
    client.cookies.set(COOKIE,token)
    assert client.get("/api/v1/me").status_code==401
    client.cookies.clear()
    assert client.post("/api/v1/auth/login",json={"email":"user@example.com","password":PASSWORD}).status_code==200
    with Session(app.state.engine) as db:
        session=db.get(AuthSession,token_digest(client.cookies.get(COOKIE),app.state.settings))
        session.expires_at=now_utc()-timedelta(seconds=1);db.commit()
    assert client.get("/api/v1/me").status_code==401


def test_invalid_credentials_csrf_auth_config(client,app):
    assert client.get("/api/v1/me").status_code==401
    register(client)
    assert client.post("/api/v1/auth/login",json={"email":"user@example.com","password":"incorrect-password"}).status_code==401
    assert client.post("/api/v1/auth/login",json={"email":"unknown@example.com","password":"incorrect-password"}).status_code==401
    assert client.put("/api/v1/me/preferences",json={},headers={"Origin":"https://evil.example"}).status_code==403
    assert client.post("/api/v1/auth/logout",headers={"X-Tencerem-CSRF":""}).status_code==403
    client.cookies.clear();client.cookies.set(COOKIE,"invalid-token")
    assert client.get("/api/v1/me").status_code==401
    assert client.post("/api/v1/auth/register",json={"email":"bad","password":"short"}).status_code==422
    assert "password_hash" not in client.get("/api/v1/me").text
    with pytest.raises(ValueError):create_app(Settings(_env_file=None,database_url="sqlite:///should-not-create.sqlite"))
    with pytest.raises(ValueError):Settings(_env_file=None,environment="production",cookie_secure=False)


def test_persistence_preferences_and_pantry_after_relogin(client):
    register(client)
    profile=save(client,dietary_pattern="standard",goals=["high_protein","quick"],liked_ingredients=["chicken_breast"],disliked_ingredients=["mushroom"],default_servings=2)
    for ident,qty,unit in [("chicken_breast",300,"g"),("rice",500,"g"),("salt",None,None)]:
        assert client.post("/api/v1/me/pantry",json={"ingredient_id":ident,"quantity":qty,"unit":unit}).status_code==201
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login",json={"email":"user@example.com","password":PASSWORD})
    assert client.get("/api/v1/me/preferences").json()==profile
    pantry=client.get("/api/v1/me/pantry").json()
    assert len(pantry)==3 and next(i for i in pantry if i["ingredient_id"]=="salt")["quantity"] is None
    # A new HTTP client/session reads persisted records as well.
    with TestClient(client.app) as other:
        other.headers.update(HEADERS)
        assert other.post("/api/v1/auth/login",json={"email":"user@example.com","password":PASSWORD}).status_code==200
        assert len(other.get("/api/v1/me/pantry").json())==3


def test_user_isolation_and_malformed_ids(client,app):
    register(client,"a@example.com")
    entry=client.post("/api/v1/me/pantry",json={"ingredient_id":"chicken_breast","quantity":500,"unit":"g"}).json()
    save(client,liked_ingredients=["chicken_breast"])
    cookie_a=client.cookies.get(COOKIE)
    with TestClient(app) as b:
        b.headers.update(HEADERS);register(b,"b@example.com")
        rice=b.post("/api/v1/me/pantry",json={"ingredient_id":"rice","quantity":1,"unit":"kg"}).json()
        assert [p["ingredient_id"] for p in b.get("/api/v1/me/pantry").json()]==["rice"]
        assert b.patch(f"/api/v1/me/pantry/{entry['id']}",json={"quantity":0}).status_code==404
        assert b.delete(f"/api/v1/me/pantry/{entry['id']}").status_code==404
        assert b.get("/api/v1/me/preferences").json()["liked_ingredients"]==[]
        assert client.patch(f"/api/v1/me/pantry/{rice['id']}",json={"quantity":0}).status_code==404
        basket=b.post("/api/v1/me/baskets/preview",json={"recipes":[{"slug":"tavuklu-pilav","servings":5}]}).json()
        chicken=next(i for i in basket["items"] if i["ingredient_id"]=="chicken_breast")["components"][0]
        assert Decimal(chicken["pantry_allocated_quantity"])==0
        a_basket=client.post("/api/v1/me/baskets/preview",json={"recipes":[{"slug":"tavuklu-pilav","servings":5}]}).json()
        a_rice=next(i for i in a_basket["items"] if i["ingredient_id"]=="rice")["components"][0]
        assert Decimal(a_rice["pantry_allocated_quantity"])==0
    assert client.patch("/api/v1/me/pantry/not-a-uuid",json={"quantity":0}).status_code==422
    assert client.delete(f"/api/v1/me/pantry/{uuid4()}").status_code==404
    assert [p["ingredient_id"] for p in client.get("/api/v1/me/pantry").json()]==["chicken_breast"]
    assert client.get("/api/v1/me/preferences").json()["liked_ingredients"]==["chicken_breast"]


def test_pantry_edit_units_expiration_saved_basket(client):
    register(client)
    row=client.post("/api/v1/me/pantry",json={"ingredient_id":"chicken_breast","quantity":300,"unit":"g","expiration_date":"2026-10-20"}).json()
    path=f"/api/v1/me/pantry/{row['id']}"
    response=client.patch(path,json={"unit":"kg"})
    assert response.status_code==200 and Decimal(response.json()["quantity"])==Decimal("0.3")
    assert client.patch(path,json={"unit":"ml"}).status_code==422
    assert client.post("/api/v1/me/pantry",json={"ingredient_id":"chicken_breast"}).status_code==409
    assert client.post("/api/v1/me/pantry",json={"ingredient_id":"invented"}).status_code==422
    assert client.post("/api/v1/me/pantry",json={"ingredient_id":"rice","quantity":-1,"unit":"g"}).status_code==422
    client.post("/api/v1/me/pantry",json={"ingredient_id":"rice","quantity":500,"unit":"g"})
    basket=client.post("/api/v1/me/baskets/preview",json={"recipes":[{"slug":"tavuklu-pilav","servings":5}]}).json()
    components={i["ingredient_id"]:i["components"][0] for i in basket["items"]}
    assert Decimal(components["chicken_breast"]["missing_quantity"])==200
    assert Decimal(components["rice"]["missing_quantity"])==0
    assert client.patch(path,json={"quantity":None,"unit":None,"expiration_date":None}).json()["quantity"] is None
    assert client.patch(path,json={"quantity":10}).status_code==422
    assert client.delete(path).status_code==204


def test_personalization_constraints_overrides_conflict(client):
    register(client)
    save(client,liked_ingredients=["chicken_breast"],goals=["high_protein"],disliked_ingredients=["mushroom"],default_max_minutes=15,default_servings=3)
    response=client.post("/api/v1/me/recipes/recommend",json={"craving":"tavuk","max_minutes":30}).json()
    assert response["applied_max_minutes"]==30 and response["applied_servings"]==3
    assert client.post("/api/v1/me/recipes/recommend",json={"max_minutes":60}).json()["applied_max_minutes"]==60
    assert client.get("/api/v1/me/preferences").json()["default_max_minutes"]==15
    assert response["recipes"] and response["recipes"][0]["personalization_signals"]["liked_matches"]==1
    assert all(r["recipe"]["total_minutes"]<=30 and "mushroom" not in {i["ingredient_id"] for i in r["recipe"]["ingredients"]} for r in response["recipes"])
    save(client,dietary_pattern="vegetarian",liked_ingredients=["chicken_breast"])
    conflict=client.post("/api/v1/me/recipes/recommend",json={"craving":"tavuk","dietary_pattern":"standard"}).json()
    assert not conflict["recipes"] and conflict["conflicts"]
    assert client.put("/api/v1/me/preferences",json={"liked_ingredients":["sql'; DROP TABLE users;--"]}).status_code==422


def test_allergy_beats_liked_and_incomplete_metadata(client,app):
    register(client)
    save(client,allergies=["milk"],liked_ingredients=["feta"])
    data=client.post("/api/v1/me/recipes/recommend",json={"craving":"yemek","max_minutes":120}).json()
    assert data["recipes"] and "tıbbi" in data["warnings"][0]
    for match in data["recipes"]:
        for ingredient in match["recipe"]["ingredients"]:
            definition=app.state.catalog.registry.get(ingredient["ingredient_id"])
            assert "milk" not in definition.allergens and definition.allergen_metadata_complete
    with pytest.raises(ValidationError):
        IngredientDefinition.model_validate({**app.state.catalog.registry.get("milk").model_dump(),"allergens":[]})


def test_dislike_override_soft_likes_goals_and_time(app):
    catalog=app.state.catalog
    profile=Preferences(disliked_ingredients=("egg",),liked_ingredients=("egg",),goals=("quick",))
    blocked=personalized_recommend(catalog,profile,MealIntent(craving="menemen",max_minutes=30),())
    assert not blocked["recipes"]
    allowed=personalized_recommend(catalog,profile,MealIntent(craving="menemen",max_minutes=30,allow_disliked=True),())
    assert allowed["recipes"][0]["recipe"]["slug"]=="menemen"
    assert allowed["recipes"][0]["personalization_signals"]["goal_matches"]==1
    assert not personalized_recommend(catalog,profile,MealIntent(craving="menemen",max_minutes=5,allow_disliked=True),())["recipes"]


def test_saved_pantry_adjustments_are_temporary(client):
    register(client)
    client.post("/api/v1/me/pantry",json={"ingredient_id":"chicken_breast","quantity":300,"unit":"g"})
    body={"recipes":[{"slug":"tavuklu-pilav","servings":5}],"pantry_adjustments":[{"ingredient_id":"chicken_breast","quantity":500,"unit":"g"}]}
    data=client.post("/api/v1/me/baskets/preview",json=body).json()
    chicken=next(i for i in data["items"] if i["ingredient_id"]=="chicken_breast")["components"][0]
    assert Decimal(chicken["missing_quantity"])==0
    assert Decimal(client.get("/api/v1/me/pantry").json()[0]["quantity"])==300


def test_cookie_secure_default_throttle_and_ownership_body(client,app):
    register(client)
    assert client.post("/api/v1/me/baskets/preview",json={"recipes":[{"slug":"tavuklu-pilav","servings":2}],"user_id":str(uuid4())}).status_code==422
    app.state.auth_attempts["testclient"]=(__import__('time').monotonic(),30)
    limited=client.post("/api/v1/auth/login",json={"email":"user@example.com","password":PASSWORD})
    assert limited.status_code==429 and limited.headers["retry-after"]=="60"
    assert Settings(_env_file=None).cookie_secure is True
    app.state.auth_attempts.clear();app.state.settings.cookie_secure=True;client.cookies.clear()
    secure=client.post("/api/v1/auth/register",json={"email":"secure@example.com","password":PASSWORD})
    assert secure.status_code==201
    cookie=secure.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie


def test_saved_basket_rejects_allergy_conflict(client):
    register(client)
    save(client,allergies=["milk"],liked_ingredients=["feta"])
    response=client.post("/api/v1/me/baskets/preview",json={"recipes":[{"slug":"peynirli-omlet","servings":2}]})
    assert response.status_code==422


def test_incomplete_metadata_fails_closed_and_soft_ranking(app):
    from copy import copy
    from app.repositories.ingredients import IngredientRegistry
    catalog=app.state.catalog
    # Unknown metadata must reject an otherwise compatible recipe under any saved allergy.
    altered=copy(catalog)
    altered.registry=IngredientRegistry(tuple(i.model_copy(update={"allergen_metadata_complete":False}) if i.id=="egg" else i for i in catalog.ingredients))
    output=personalized_recommend(altered,Preferences(allergies=("peanut",)),MealIntent(craving="menemen"),())
    assert not output["recipes"]
    base=personalized_recommend(catalog,Preferences(),MealIntent(craving="yemek",max_minutes=120),())
    liked=personalized_recommend(catalog,Preferences(liked_ingredients=("chicken_breast",)),MealIntent(craving="yemek",max_minutes=120),())
    assert liked["recipes"][0]["personalization_signals"]["liked_matches"]==1
    assert base["recipes"][0]["recipe"]["slug"] != liked["recipes"][0]["recipe"]["slug"]


def test_expiration_with_non_utc_database_timezone(app):
    from types import SimpleNamespace
    from datetime import timezone
    from fastapi import HTTPException
    from app.services.auth import current_user
    expired=(now_utc()-timedelta(seconds=5)).astimezone(timezone(timedelta(hours=3)))
    class FakeDatabase:
        def get(self, model, key):
            return SimpleNamespace(expires_at=expired,user_id="ignored")
    request=SimpleNamespace(app=app,cookies={COOKIE:"test-token"})
    with pytest.raises(HTTPException) as error:current_user(request,FakeDatabase())
    assert error.value.status_code==401
