from quart import Quart, current_app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from contextlib import asynccontextmanager
from typing import AsyncGenerator

Base = declarative_base()


async def init_db(app: Quart):
    engine = create_async_engine(app.config.get("DATABASE_URI"), echo=True)
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

    app.config['db_engine'] = engine
    app.config['SessionLocal'] = SessionLocal


async def create_tables(app: Quart):
    from app.models.chat import Chat
    from app.models.authentication import Authentication
    from app.models.loginhistory import LoginHistory
    from app.models.file import File
    from app.models.folder import Folder
    from app.models.recruitment import Recruitment

    engine: AsyncEngine = app.config.get('db_engine')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """session"""
    session: AsyncSession = current_app.config['SessionLocal']()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """transaction session"""
    async with get_db_session() as session:
        async with session.begin():
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise e
            else:
                await session.commit()
