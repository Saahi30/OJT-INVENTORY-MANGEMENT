"""
Inventory reservation API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.services.inventory_service import InventoryService
from app.schemas import (
    CreateHoldRequest, CreateAllocationRequest, ConvertHoldRequest,
    ReleaseHoldRequest, ReservationResponse, AvailabilityResponse,
    ConsistencyCheckResponse, ErrorResponse
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.post("/holds", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_hold(
    request: CreateHoldRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a hold reservation.
    
    - **client_token**: Idempotency token (required)
    - **items**: List of SKU and quantity pairs
    - **expires_in_seconds**: Hold expiry duration
    - **strategy**: "optimistic" or "pessimistic" locking strategy
    """
    service = InventoryService(db)
    reservation, error = await service.create_hold(
        client_token=request.client_token,
        items=request.items,
        user_id=request.user_id,
        expires_in_seconds=request.expires_in_seconds,
        strategy=request.strategy,
        metadata=request.metadata
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return reservation


@router.post("/allocations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_allocation(
    request: CreateAllocationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a direct allocation (without hold).
    
    This creates a hold and immediately converts it to allocation.
    """
    service = InventoryService(db)
    
    # Create hold first
    reservation, error = await service.create_hold(
        client_token=request.client_token,
        items=request.items,
        user_id=request.user_id,
        expires_in_seconds=1,  # Very short expiry
        strategy=request.strategy,
        metadata=request.metadata
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Immediately convert to allocation
    reservation, error = await service.convert_hold_to_allocation(reservation.reservation_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return reservation


@router.post("/holds/{reservation_id}/convert", response_model=ReservationResponse)
async def convert_hold(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Convert a hold to allocation.
    """
    service = InventoryService(db)
    reservation, error = await service.convert_hold_to_allocation(reservation_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return reservation


@router.post("/holds/{reservation_id}/release", response_model=ReservationResponse)
async def release_hold(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Release a hold, returning inventory to available.
    """
    service = InventoryService(db)
    reservation, error = await service.release_hold(reservation_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return reservation


@router.get("/availability", response_model=List[AvailabilityResponse])
async def get_availability(
    sku_ids: Optional[List[UUID]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get availability snapshot for SKU(s).
    
    - If no sku_ids provided, returns all SKUs
    - If sku_ids provided, returns only those SKUs
    """
    service = InventoryService(db)
    availability = await service.get_availability(sku_ids)
    
    return availability


@router.get("/consistency", response_model=ConsistencyCheckResponse)
async def check_consistency(
    db: AsyncSession = Depends(get_db)
):
    """
    Check inventory consistency across all SKUs.
    
    Verifies that available_qty = total_qty - reserved_qty - allocated_qty
    and that no negative values exist.
    """
    service = InventoryService(db)
    report = await service.check_consistency()
    
    return report

