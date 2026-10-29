from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models import Base
from app.config import settings

cfg = settings()
engine = create_async_engine(cfg.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    # Development bootstrap; use Alembic migrations before production.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
