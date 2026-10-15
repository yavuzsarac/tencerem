from fastapi import FastAPI, Request
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


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Tencerem API", version="0.3.0")
    app.state.settings = settings or Settings()
    app.state.catalog = RecipeCatalog()  # Validate curated data on application creation.
    app.add_middleware(CORSMiddleware, allow_origins=app.state.settings.cors_origins,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.add_api_route("/health", health, methods=["GET"])
    app.include_router(router, prefix="/api/v1")
    app.include_router(recipe_router, prefix="/api/v1")

    app.include_router(basket_router, prefix="/api/v1")

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
