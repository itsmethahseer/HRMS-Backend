from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(settings.async_database_url, echo=True, future=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """Gets a standard session (defaults to public schema)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_tenant_db(tenant_schema: str) -> AsyncSession:
    """Gets a tenant-aware session that routes all queries to the tenant's schema"""
    async with AsyncSessionLocal(bind=engine.execution_options(schema_translate_map={None: tenant_schema})) as session:
        try:
            yield session
        finally:
            await session.close()
