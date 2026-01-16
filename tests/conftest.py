import pytest
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_health_insurance.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client() -> Generator:
    """Create a sync test client (doesn't require db_session)."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator:
    """Create an async test client with database session override."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
