"""Offline HTTP smoke: run from backend with .venv/Scripts/python ../scripts/assistant-smoke.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings


class FakeProvider:
    async def parse_meal_intent(self, text, previous):
        return {"max_minutes":30,"goals":["high_protein"],"pantry_ingredients":["tavuk"]}

    async def choose_candidate(self, intent, candidates):
        return {"slug":candidates[0]["slug"],"reason_codes":["time","pantry"]}


application=create_app(Settings(_env_file=None))
application.state.ai_provider=FakeProvider()
with TestClient(application) as client:
    client.headers.update({"Origin":"http://localhost:3000","X-Tencerem-CSRF":"1"})
    first=client.post("/api/v1/assistant/recommend",json={"text":"Evde tavuk var, 30 dakikadan uzun sürmesin ve proteinli olsun."})
    assert first.status_code==200,first.text
    data=first.json()
    assert data["engine"]=="ai_assisted" and len(data["recommendations"]["recipes"])==1
    again=client.post("/api/v1/assistant/recommend",json={"text":"Başka öner","previous_intent":data["intent"],"shown_slugs":[data["selected_slug"]]})
    assert again.status_code==200 and again.json()["selected_slug"]!=data["selected_slug"]
    application.state.ai_provider=None
    fallback=client.post("/api/v1/assistant/recommend",json={"text":"4 kişilik yemek öner"})
    assert fallback.status_code==200 and fallback.json()["engine"]=="deterministic_fallback"
    assert fallback.json()["recommendations"]["requested_servings"]==4
print("PASS: fake-provider HTTP intent, candidate choice, no-repeat and disabled-provider fallback; no live AI or database")
