"""
Tests for inventory service.
"""
import pytest
from uuid import uuid4
from app.services.inventory_service import InventoryService
from app.schemas import SKUItem
from app.models import ReservationStatus, ReservationType


@pytest.mark.asyncio
async def test_create_hold_success(db_session, sample_sku):
    """Test successful hold creation."""
    service = InventoryService(db_session)
    
    reservation, error = await service.create_hold(
        client_token="test-token-1",
        items=[SKUItem(sku_id=sample_sku.sku_id, qty=10)],
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    
    assert error is None
    assert reservation is not None
    assert reservation.status == ReservationStatus.HELD
    assert reservation.type == ReservationType.HOLD
    assert len(reservation.items) == 1
    assert reservation.items[0].qty == 10
    
    # Check inventory was updated
    from sqlalchemy import select
    from app.models import Inventory
    result = await db_session.execute(
        select(Inventory).where(Inventory.sku_id == sample_sku.sku_id)
    )
    inventory = result.scalar_one()
    assert inventory.reserved_qty == 10
    assert inventory.total_qty - inventory.reserved_qty - inventory.allocated_qty == 90


@pytest.mark.asyncio
async def test_create_hold_insufficient_inventory(db_session, sample_sku):
    """Test hold creation with insufficient inventory."""
    service = InventoryService(db_session)
    
    reservation, error = await service.create_hold(
        client_token="test-token-2",
        items=[SKUItem(sku_id=sample_sku.sku_id, qty=200)],  # More than available
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    
    assert reservation is None
    assert error is not None
    assert "Insufficient inventory" in error


@pytest.mark.asyncio
async def test_create_hold_idempotency(db_session, sample_sku):
    """Test idempotency - same client_token returns existing reservation."""
    service = InventoryService(db_session)
    client_token = "test-token-3"
    
    # Create first hold
    reservation1, error1 = await service.create_hold(
        client_token=client_token,
        items=[SKUItem(sku_id=sample_sku.sku_id, qty=10)],
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    
    assert error1 is None
    assert reservation1 is not None
    
    # Try to create again with same token
    reservation2, error2 = await service.create_hold(
        client_token=client_token,
        items=[SKUItem(sku_id=sample_sku.sku_id, qty=10)],
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    
    assert error2 is None
    assert reservation2 is not None
    assert reservation2.reservation_id == reservation1.reservation_id


@pytest.mark.asyncio
async def test_batch_hold_success(db_session, multiple_skus):
    """Test batch hold with multiple SKUs."""
    service = InventoryService(db_session)
    
    items = [SKUItem(sku_id=sku.sku_id, qty=10) for sku in multiple_skus]
    
    reservation, error = await service.create_hold(
        client_token="test-token-batch",
        items=items,
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    
    assert error is None
    assert reservation is not None
    assert len(reservation.items) == 3
    
    # Check all inventories were updated
    from sqlalchemy import select
    from app.models import Inventory
    for sku in multiple_skus:
        result = await db_session.execute(
            select(Inventory).where(Inventory.sku_id == sku.sku_id)
        )
        inventory = result.scalar_one()
        assert inventory.reserved_qty == 10


@pytest.mark.asyncio
async def test_convert_hold_to_allocation(db_session, sample_sku):
    """Test converting a hold to allocation."""
    service = InventoryService(db_session)
    
    # Create hold
    reservation, error = await service.create_hold(
        client_token="test-token-convert",
        items=[SKUItem(sku_id=sample_sku.sku_id, qty=10)],
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    assert error is None
    
    # Convert to allocation
    converted, error = await service.convert_hold_to_allocation(reservation.reservation_id)
    
    assert error is None
    assert converted.status == ReservationStatus.ALLOCATED
    
    # Check inventory: reserved should decrease, allocated should increase
    from sqlalchemy import select
    from app.models import Inventory
    result = await db_session.execute(
        select(Inventory).where(Inventory.sku_id == sample_sku.sku_id)
    )
    inventory = result.scalar_one()
    assert inventory.reserved_qty == 0
    assert inventory.allocated_qty == 10


@pytest.mark.asyncio
async def test_release_hold(db_session, sample_sku):
    """Test releasing a hold."""
    service = InventoryService(db_session)
    
    # Create hold
    reservation, error = await service.create_hold(
        client_token="test-token-release",
        items=[SKUItem(sku_id=sample_sku.sku_id, qty=10)],
        user_id=None,
        expires_in_seconds=300,
        strategy="optimistic"
    )
    assert error is None
    
    # Release hold
    released, error = await service.release_hold(reservation.reservation_id)
    
    assert error is None
    assert released.status == ReservationStatus.RELEASED
    
    # Check inventory: reserved should be back to 0
    from sqlalchemy import select
    from app.models import Inventory
    result = await db_session.execute(
        select(Inventory).where(Inventory.sku_id == sample_sku.sku_id)
    )
    inventory = result.scalar_one()
    assert inventory.reserved_qty == 0
    assert inventory.allocated_qty == 0


@pytest.mark.asyncio
async def test_get_availability(db_session, sample_sku):
    """Test getting availability snapshot."""
    service = InventoryService(db_session)
    
    availability = await service.get_availability([sample_sku.sku_id])
    
    assert len(availability) == 1
    assert availability[0]["sku_id"] == sample_sku.sku_id
    assert availability[0]["total_qty"] == 100
    assert availability[0]["available_qty"] == 100


@pytest.mark.asyncio
async def test_consistency_check(db_session, sample_sku):
    """Test consistency check."""
    service = InventoryService(db_session)
    
    report = await service.check_consistency()
    
    assert report["is_consistent"] is True
    assert report["total_skus"] == 1
    assert len(report["inconsistent_skus"]) == 0

