"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import SKU, Inventory
from uuid import uuid4


# Test database URL (using in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    """Create a test client."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_sku(db_session):
    """Create a sample SKU with inventory."""
    sku = SKU(
        sku_id=uuid4(),
        sku_code="TEST-SKU-001",
        name="Test Product",
        description="Test description"
    )
    db_session.add(sku)
    await db_session.flush()
    
    inventory = Inventory(
        sku_id=sku.sku_id,
        total_qty=100,
        reserved_qty=0,
        allocated_qty=0,
        version=1
    )
    db_session.add(inventory)
    await db_session.commit()
    await db_session.refresh(sku)
    
    return sku


@pytest.fixture
async def multiple_skus(db_session):
    """Create multiple sample SKUs."""
    skus = []
    for i in range(3):
        sku = SKU(
            sku_id=uuid4(),
            sku_code=f"TEST-SKU-{i+1:03d}",
            name=f"Test Product {i+1}",
            description=f"Test description {i+1}"
        )
        db_session.add(sku)
        await db_session.flush()
        
        inventory = Inventory(
            sku_id=sku.sku_id,
            total_qty=100,
            reserved_qty=0,
            allocated_qty=0,
            version=1
        )
        db_session.add(inventory)
        skus.append(sku)
    
    await db_session.commit()
    return skus

