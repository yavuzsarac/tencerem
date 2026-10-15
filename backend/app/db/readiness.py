from sqlalchemy import create_engine, text
from app.core.config import Settings


def check_database(settings: Settings) -> str:
    if settings.database_url is None:
        return "not_configured"
    engine = None
    try:
        url = settings.database_url.get_secret_value()
        if not url.startswith("postgresql+psycopg://"):
            return "unavailable"
        engine = create_engine(url, connect_args={"connect_timeout": 3}, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        # Never return connection strings, credentials, or driver messages.
        return "unavailable"
    finally:
        if engine is not None:
            engine.dispose()
