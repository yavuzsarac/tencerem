from alembic import context
from app.core.config import Settings
from app.db.session import make_engine
from app.models.users import Base

config=context.config
settings=Settings()
# Tests inject an isolated connection; production always uses environment PostgreSQL.
connection=config.attributes.get("connection")
if context.is_offline_mode():
    context.configure(url="postgresql+psycopg://",target_metadata=Base.metadata,literal_binds=True,dialect_opts={"paramstyle":"named"})
    with context.begin_transaction():context.run_migrations()
else:
    engine=None
    if connection is None:
        engine=make_engine(settings)
        if engine is None:raise RuntimeError("DATABASE_URL must be configured for migrations")
        connection=engine.connect()
    try:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
    finally:
        if engine is not None:connection.close(); engine.dispose()
