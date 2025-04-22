import os

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = os.environ['DATABASE_URL']

engine = create_async_engine(DATABASE_URL)


async def get_session():
    async with AsyncSession(engine) as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
