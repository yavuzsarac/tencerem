from fastapi import APIRouter, Depends, Request, HTTPException
from time import monotonic
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.services.assistant import decide
from app.services.auth import current_user, csrf
from app.services.profiles import read_preferences, saved_pantry

router = APIRouter(tags=["meal decisions"])


def limit_decisions(request: Request):
    # Local abuse/cost brake, independent from authentication attempt limits.
    now = monotonic()
    key = request.client.host if request.client else "unknown"
    with request.app.state.auth_lock:
        buckets = request.app.state.decision_attempts
        for old in [k for k, (start, _) in buckets.items() if now-start >= 60]: del buckets[old]
        start, count = buckets.get(key, (now, 0))
        if count >= 15 or (key not in buckets and len(buckets) >= 10000):
            raise HTTPException(429, "Çok fazla karar isteği. Bir dakika sonra tekrar dene.", headers={"Retry-After":"60"})
        buckets[key] = (start, count+1)


@router.post("/assistant/recommend", response_model=AssistantResponse, dependencies=[Depends(csrf), Depends(limit_decisions)])
async def recommend(body: AssistantRequest, request: Request):
    return await decide(request.app.state.catalog, request.app.state.settings,
                        request.app.state.ai_provider, body)


@router.post("/me/assistant/recommend", response_model=AssistantResponse, dependencies=[Depends(csrf), Depends(limit_decisions)])
async def recommend_saved(body: AssistantRequest, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile, pantry = read_preferences(db, user.id), saved_pantry(db, user.id)
    db.rollback()  # Release the read transaction/connection before network waits.
    return await decide(request.app.state.catalog, request.app.state.settings,
                        request.app.state.ai_provider, body, profile, pantry)
