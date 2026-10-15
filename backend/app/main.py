from fastapi import FastAPI, Request
from threading import Lock
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from app.api.routes import router, health
from app.core.config import Settings
from app.api.recipes import router as recipe_router
from app.repositories.catalog import RecipeCatalog
from app.api.baskets import router as basket_router
from app.services.pantry import BasketInputError
from app.db.session import make_engine
from app.api.accounts import router as account_router
from sqlalchemy.exc import OperationalError
from pydantic import ValidationError
from app.api.assistant import router as assistant_router
from app.services.ai_provider import build_provider


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Tencerem API", version="0.4.0")
    app.state.settings = settings or Settings()
    app.state.ai_provider = build_provider(app.state.settings)
    app.state.auth_attempts = {}
    app.state.decision_attempts = {}
    app.state.auth_lock = Lock()
    app.state.engine = make_engine(app.state.settings)
    app.state.catalog = RecipeCatalog()  # Validate curated data on application creation.
    app.add_middleware(CORSMiddleware, allow_origins=app.state.settings.cors_origins,
                       allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-Tencerem-CSRF"])
    app.add_api_route("/health", health, methods=["GET"])
    app.include_router(router, prefix="/api/v1")
    app.include_router(recipe_router, prefix="/api/v1")

    app.include_router(basket_router, prefix="/api/v1")

    app.include_router(account_router, prefix="/api/v1")
    app.include_router(assistant_router, prefix="/api/v1")

    @app.middleware("http")
    async def private_no_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/api/v1/auth", "/api/v1/me", "/api/v1/assistant")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(OperationalError)
    async def database_unavailable(request: Request, exc: OperationalError):
        return JSONResponse(status_code=503, content={"error":{"code":"database_unavailable","message":"Hesap veritabanına ulaşılamıyor. Yapılandırma ve migration durumunu kontrol edin."}})

    @app.exception_handler(ValidationError)
    async def domain_validation(request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"error":{"code":"validation_error","message":"Miktar ve birimi birlikte kontrol edin."}})

    @app.exception_handler(BasketInputError)
    async def basket_input_error(request: Request, exc: BasketInputError):
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Sepet bilgilerini kontrol edin.", "fields": [{"field": exc.field, "message": str(exc)}]}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Geçersiz tercih bilgileri.", "fields": fields}})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                            content={"error": {"code": "http_error", "message": exc.detail if isinstance(exc.detail, str) else "İstek işlenemedi."}})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "Beklenmeyen bir hata oluştu."}})
    return app

app = create_app()
