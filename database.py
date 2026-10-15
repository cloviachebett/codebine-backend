import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
    if "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or "pytest" in sys.argv
    else "postgresql+asyncpg://postgres:postgres@localhost:5432/TerraWatch_db",
)

is_sqlite = DATABASE_URL.startswith("sqlite+aiosqlite")

if is_sqlite:
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
    # Create all tables defined in models.

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
