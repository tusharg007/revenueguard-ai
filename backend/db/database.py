from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    connect_args = {}
    database_url = make_url(settings.DATABASE_URL)
    if database_url.drivername in ("postgres", "postgresql"):
        database_url = database_url.set(drivername="postgresql+asyncpg")
    if database_url.drivername == "postgresql+asyncpg":
        # Hosted Postgres URLs contain libpq options that asyncpg cannot accept.
        sslmode = database_url.query.get("sslmode")
        database_url = database_url.difference_update_query(["channel_binding", "sslmode"])
        if sslmode is not None:
            connect_args["ssl"] = sslmode
    if database_url.get_backend_name() == "sqlite":
        connect_args["check_same_thread"] = False
    return create_async_engine(
        database_url,
        echo=settings.APP_ENV == "development",
        connect_args=connect_args,
    )


engine = None
async_session_maker = None


def init_engine():
    global engine, async_session_maker
    engine = get_engine()
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    global async_session_maker
    if async_session_maker is None:
        init_engine()
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
