from pathlib import Path
from typing import Literal
from pydantic import SecretStr, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")
    database_url: SecretStr | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    environment: Literal["development", "production", "test"] = "development"
    allow_test_sqlite: bool = False
    auth_secret: SecretStr | None = None
    cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    @model_validator(mode="after")
    def secure_production(self):
        if self.environment == "production" and (not self.cookie_secure or "*" in self.cors_origins):
            raise ValueError("Production requires Secure cookies and explicit origins")
        return self
