import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import Config
from sqlmodel.ext.asyncio.session import AsyncSession

# Lambda: each invocation may run in a different container, so connection pools
# across instances cause exhaustion on Neon. NullPool creates/closes a fresh
# connection per request — safe for serverless, fine with Neon's own pooler.
_IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False,
    **({"poolclass": NullPool} if _IS_LAMBDA else {}),
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
