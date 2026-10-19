import os

# Тесты работают с отдельной базой, чтобы не трогать рабочие данные.
# Переменные окружения важнее .env, поэтому это нужно сделать ДО импорта app.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://restaurant:restaurant@localhost:5433/restaurant_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-pytest-1234567890")

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.database import Base, engine
from app.main import app
from app.models import UserRole
from app.rate_limit import login_limiter
from tests.helpers import create_user


async def ensure_test_database():
    """Создаёт базу restaurant_test, если её ещё нет."""
    url = make_url(TEST_DATABASE_URL)
    conn = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", url.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    # страховка: рабочую базу тесты не трогают никогда
    assert engine.url.database.endswith("_test"), "Тесты должны идти в базу *_test"

    await ensure_test_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables():
    """Перед каждым тестом очищаем все таблицы, чтобы тесты не влияли друг на друга."""
    names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    # счётчик неудачных входов живёт в памяти, его тоже сбрасываем
    login_limiter.failures.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def admin():
    return await create_user("admin", UserRole.admin)


@pytest.fixture
async def customer():
    return await create_user("customer")