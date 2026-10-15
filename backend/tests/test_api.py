import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings

@pytest.fixture
def client():
    return TestClient(create_app(Settings(_env_file=None, database_url=None)))

@pytest.fixture
def payload():
    return {"craving": "Mercimek çorbası", "servings": 2, "max_budget_try": "350.50", "max_prep_minutes": 30, "dietary_preference": "vegan"}

def test_liveness_and_unconfigured_readiness(client):
    for path in ["/health", "/api/v1/health"]:
        assert client.get(path).json()["status"] == "ok"
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["database"] == "not_configured"

def test_development_receipt(client, payload):
    response = client.post("/api/v1/meal-preferences", json=payload)
    assert response.status_code == 200
    assert response.json()["mode"] == "development"
    assert response.json()["preferences"] == payload

@pytest.mark.parametrize("field,value", [("craving", "   "), ("servings", 0), ("servings", 1.5), ("max_budget_try", -1), ("max_budget_try", "12.345"), ("max_prep_minutes", 241), ("dietary_preference", "unknown")])
def test_invalid_preferences(client, payload, field, value):
    payload[field] = value
    response = client.post("/api/v1/meal-preferences", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

def test_database_probe_success_and_failure(monkeypatch):
    from app.db import readiness
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement): assert str(statement) == "SELECT 1"
    class Engine:
        disposed = False
        def connect(self): return Connection()
        def dispose(self): self.disposed = True
    engine = Engine()
    monkeypatch.setattr(readiness, "create_engine", lambda *a, **kw: engine)
    client = TestClient(create_app(Settings(_env_file=None, database_url="postgresql+psycopg://user:secret@localhost/db")))
    assert client.get("/api/v1/ready").json() == {"status": "ready", "database": "connected"}
    assert engine.disposed
    def fail(*a, **kw): raise RuntimeError("private credential")
    monkeypatch.setattr(readiness, "create_engine", fail)
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert "private" not in response.text

def test_unknown_route_and_cors(client):
    assert client.get("/missing").json()["error"]["code"] == "http_error"
    response = client.options("/api/v1/meal-preferences", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
