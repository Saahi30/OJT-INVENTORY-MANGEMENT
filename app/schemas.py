"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models import ReservationStatus, ReservationType


class SKUItem(BaseModel):
    """SKU and quantity pair for batch operations."""
    sku_id: UUID
    qty: int = Field(gt=0, description="Quantity must be positive")
    
    class Config:
        from_attributes = True


class CreateHoldRequest(BaseModel):
    """Request to create a hold."""
    client_token: str = Field(..., description="Idempotency token")
    items: List[SKUItem] = Field(..., min_length=1, description="List of SKUs and quantities")
    user_id: Optional[UUID] = None
    expires_in_seconds: int = Field(300, gt=0, description="Hold expiry duration in seconds")
    strategy: str = Field("optimistic", pattern="^(optimistic|pessimistic)$", description="Locking strategy")
    metadata: Optional[dict] = None


class CreateAllocationRequest(BaseModel):
    """Request to create a direct allocation (without hold)."""
    client_token: str = Field(..., description="Idempotency token")
    items: List[SKUItem] = Field(..., min_length=1, description="List of SKUs and quantities")
    user_id: Optional[UUID] = None
    strategy: str = Field("optimistic", pattern="^(optimistic|pessimistic)$", description="Locking strategy")
    metadata: Optional[dict] = None


class ConvertHoldRequest(BaseModel):
    """Request to convert a hold to allocation."""
    reservation_id: UUID


class ReleaseHoldRequest(BaseModel):
    """Request to release a hold."""
    reservation_id: UUID


class ReservationItemResponse(BaseModel):
    """Reservation item response."""
    reservation_item_id: UUID
    sku_id: UUID
    qty: int
    unit_price: Optional[float] = None
    
    class Config:
        from_attributes = True


class ReservationResponse(BaseModel):
    """Reservation response."""
    reservation_id: UUID
    client_token: str
    user_id: Optional[UUID]
    status: ReservationStatus
    type: ReservationType
    total_items: int
    requested_at: datetime
    expires_at: Optional[datetime]
    completed_at: Optional[datetime]
    items: List[ReservationItemResponse]
    metadata: Optional[dict] = None
    
    class Config:
        from_attributes = True


class AvailabilityResponse(BaseModel):
    """Availability snapshot response."""
    sku_id: UUID
    total_qty: int
    reserved_qty: int
    allocated_qty: int
    available_qty: int
    version: int
    
    class Config:
        from_attributes = True


class ConsistencyCheckResponse(BaseModel):
    """Consistency check response."""
    is_consistent: bool
    total_skus: int
    inconsistent_skus: List[dict]
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None

