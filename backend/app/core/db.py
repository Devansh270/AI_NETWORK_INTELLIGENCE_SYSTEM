import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


def get_database_url():
    user = os.getenv("POSTGRES_USER", "dev")
    password = os.getenv("POSTGRES_PASSWORD", "devpass")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "appdb")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL = get_database_url()

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
