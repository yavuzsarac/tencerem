import hashlib
import hmac
import secrets
from datetime import timedelta, timezone
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from app.db.session import get_db
from app.models.users import AuthSession, User, now_utc

COOKIE = "tencerem_session"
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


def verify_password(encoded: str, password: str) -> bool:
    try:
        return HASHER.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def auth_settings(request: Request):
    settings = request.app.state.settings
    if settings.auth_secret is None or len(settings.auth_secret.get_secret_value()) < 32 or settings.auth_secret.get_secret_value().startswith("REPLACE_"):
        raise HTTPException(503, "Hesap servisi için AUTH_SECRET yapılandırılmalı.")
    return settings


def token_digest(token: str, settings) -> str:
    return hmac.new(settings.auth_secret.get_secret_value().encode(), token.encode(), hashlib.sha256).hexdigest()


def csrf(request: Request):
    settings = request.app.state.settings
    if request.headers.get("origin") not in settings.cors_origins or request.headers.get("x-tencerem-csrf") != "1":
        raise HTTPException(403, "İstek kaynağı doğrulanamadı. Sayfayı yenileyip tekrar deneyin.")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = auth_settings(request)
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 128:
        raise HTTPException(401, "Lütfen giriş yapın.")
    session = db.get(AuthSession, token_digest(token, settings))
    expires = None if session is None else session.expires_at
    if expires is not None:
        expires = expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires.astimezone(timezone.utc)
    if session is None or expires <= now_utc():
        raise HTTPException(401, "Oturum geçersiz veya süresi doldu. Tekrar giriş yapın.")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "Lütfen tekrar giriş yapın.")
    return user


def issue_session(request: Request, response: Response, db: Session, user: User):
    settings = auth_settings(request)
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(old, settings)))
    # Opportunistic cleanup, no refresh tokens or background jobs.
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now_utc()))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_digest(token, settings), user_id=user.id,
        expires_at=now_utc()+timedelta(seconds=settings.session_ttl_seconds)))
    response.set_cookie(COOKIE, token, max_age=settings.session_ttl_seconds, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/")


def throttle_auth(request: Request):
    # Bounded, process-local fallback. Public deployments also need ingress limits.
    from time import monotonic
    bucket = request.app.state.auth_attempts
    current = monotonic()
    key = request.client.host if request.client else "unknown"
    with request.app.state.auth_lock:
        for old_key in [k for k, (start, _) in bucket.items() if current-start >= 60]:
            del bucket[old_key]
        start, count = bucket.get(key, (current, 0))
        if count >= 30 or (key not in bucket and len(bucket) >= 10000):
            raise HTTPException(429,"Çok fazla giriş denemesi. Bir dakika sonra tekrar deneyin.",headers={"Retry-After":"60"})
        bucket[key] = (start,count+1)
