import os

os.environ["VCW_DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"
os.environ["VCW_ACCESS_SECRET"] = "test-access-secret-with-more-than-32-bytes"
os.environ["VCW_ADMIN_EMAIL"] = "admin@example.com"
os.environ["VCW_ADMIN_PASSWORD"] = "AdminPassword123!"

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import engine, init_database
from app.main import app
from app.models import Base
from app.seed import seed


@pytest.fixture(autouse=True)
async def reset_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await init_database()
    await seed()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as value:
        yield value
