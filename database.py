import os
import sys

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
    if "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or "pytest" in sys.argv
    else "postgresql+asyncpg://postgres:postgres@localhost:5432/TerraWatch_db",
)

is_async = not DATABASE_URL.startswith("sqlite://")

if is_async:
    if DATABASE_URL.startswith("sqlite+aiosqlite"):
        engine = create_async_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            pool_pre_ping=True,
        )
    else:
        engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
        )
    SessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession,
    )
    Base = declarative_base()

    async def get_db() -> AsyncSession:
        async with SessionLocal() as session:
            yield session

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if "sqlite" in engine.url.drivername:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON;")
            finally:
                cursor.close()

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base = declarative_base()

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_tables():
        Base.metadata.create_all(bind=engine)
