from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.db.readiness import check_database
from app.schemas.preferences import MealPreferences, PreferenceReceipt

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tencerem-api"}

@router.get("/ready")
def ready(request: Request):
    database = check_database(request.app.state.settings)
    return JSONResponse(status_code=200 if database == "connected" else 503,
                        content={"status": "ready" if database == "connected" else "not_ready", "database": database})

@router.post("/meal-preferences", response_model=PreferenceReceipt)
def submit_preferences(preferences: MealPreferences) -> PreferenceReceipt:
    return PreferenceReceipt(preferences=preferences)
