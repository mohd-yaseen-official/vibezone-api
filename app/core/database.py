from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
	db = AsyncSessionLocal()
	try:
		yield db
	finally:
		await db.close()

SYNC_DATABASE_URL = settings.database_url.replace("asyncpg", "psycopg2")
sync_engine = create_engine(SYNC_DATABASE_URL, future=True)
SyncSessionLocal = sessionmaker(bind=sync_engine)