"""
SKU management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, List
from app.database import get_db
from app.models import SKU, Inventory

router = APIRouter(prefix="/api/v1/skus", tags=["skus"])


class CreateSKURequest(BaseModel):
    """Request to create a SKU."""
    sku_code: str = Field(..., description="Unique SKU code")
    name: str
    description: Optional[str] = None
    attributes: Optional[dict] = None
    initial_qty: int = Field(0, ge=0, description="Initial inventory quantity")


class SKUResponse(BaseModel):
    """SKU response."""
    sku_id: UUID
    sku_code: str
    name: str
    description: Optional[str]
    attributes: Optional[dict]
    
    class Config:
        from_attributes = True


class SKUWithInventoryResponse(BaseModel):
    """SKU response with inventory information."""
    sku_id: UUID
    sku_code: str
    name: str
    description: Optional[str]
    attributes: Optional[dict]
    total_qty: int
    reserved_qty: int
    allocated_qty: int
    available_qty: int
    
    class Config:
        from_attributes = True


@router.post("", response_model=SKUResponse, status_code=status.HTTP_201_CREATED)
async def create_sku(
    request: CreateSKURequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new SKU with initial inventory.
    """
    # Check if SKU code already exists
    existing = await db.execute(
        select(SKU).where(SKU.sku_code == request.sku_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SKU with code {request.sku_code} already exists"
        )
    
    # Create SKU
    sku = SKU(
        sku_code=request.sku_code,
        name=request.name,
        description=request.description,
        attributes=request.attributes
    )
    db.add(sku)
    await db.flush()
    
    # Create inventory record
    inventory = Inventory(
        sku_id=sku.sku_id,
        total_qty=request.initial_qty,
        reserved_qty=0,
        allocated_qty=0
    )
    db.add(inventory)
    await db.commit()
    await db.refresh(sku)
    
    return sku


@router.get("", response_model=List[SKUWithInventoryResponse])
async def list_skus(
    db: AsyncSession = Depends(get_db)
):
    """
    List all SKUs with their inventory information.
    """
    result = await db.execute(
        select(SKU)
        .options(selectinload(SKU.inventory))
        .order_by(SKU.sku_code)
    )
    skus = result.scalars().all()
    
    response = []
    for sku in skus:
        inventory = sku.inventory
        if inventory:
            response.append({
                "sku_id": sku.sku_id,
                "sku_code": sku.sku_code,
                "name": sku.name,
                "description": sku.description,
                "attributes": sku.attributes,
                "total_qty": inventory.total_qty,
                "reserved_qty": inventory.reserved_qty,
                "allocated_qty": inventory.allocated_qty,
                "available_qty": inventory.total_qty - inventory.reserved_qty - inventory.allocated_qty
            })
        else:
            # SKU exists but no inventory record (shouldn't happen, but handle gracefully)
            response.append({
                "sku_id": sku.sku_id,
                "sku_code": sku.sku_code,
                "name": sku.name,
                "description": sku.description,
                "attributes": sku.attributes,
                "total_qty": 0,
                "reserved_qty": 0,
                "allocated_qty": 0,
                "available_qty": 0
            })
    
    return response


@router.get("/{sku_id}", response_model=SKUResponse)
async def get_sku(
    sku_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a SKU by ID.
    """
    result = await db.execute(select(SKU).where(SKU.sku_id == sku_id))
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found"
        )
    
    return sku

