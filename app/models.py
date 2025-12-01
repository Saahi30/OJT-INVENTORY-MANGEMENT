"""
Database models for the inventory reservation service.
"""
from sqlalchemy import (
    Column, String, BigInteger, Integer, DateTime, Text, 
    ForeignKey, CheckConstraint, UniqueConstraint, Enum as SQLEnum,
    Numeric, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from app.database import Base


class ReservationStatus(str, enum.Enum):
    """Reservation status enum."""
    PENDING = "PENDING"
    HELD = "HELD"
    ALLOCATED = "ALLOCATED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReservationType(str, enum.Enum):
    """Reservation type enum."""
    HOLD = "HOLD"
    ALLOCATE = "ALLOCATE"


class AuditOperation(str, enum.Enum):
    """Audit log operation types."""
    HOLD_CREATED = "HOLD_CREATED"
    HOLD_RELEASED = "HOLD_RELEASED"
    ALLOCATED = "ALLOCATED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    INVENTORY_ADJUST = "INVENTORY_ADJUST"
    MANUAL_ADJUST = "MANUAL_ADJUST"


class SKU(Base):
    """Product/stock-keeping unit metadata."""
    __tablename__ = "skus"
    
    sku_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    attributes = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="sku", uselist=False)
    reservation_items = relationship("ReservationItem", back_populates="sku")


class Inventory(Base):
    """Canonical inventory state per SKU."""
    __tablename__ = "inventory"
    
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.sku_id", ondelete="CASCADE"), primary_key=True)
    total_qty = Column(BigInteger, nullable=False, default=0)
    reserved_qty = Column(BigInteger, nullable=False, default=0)
    allocated_qty = Column(BigInteger, nullable=False, default=0)
    version = Column(BigInteger, nullable=False, default=1)  # For optimistic locking
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    sku = relationship("SKU", back_populates="inventory")
    
    __table_args__ = (
        CheckConstraint("total_qty >= 0", name="check_total_qty_non_negative"),
        CheckConstraint("reserved_qty >= 0", name="check_reserved_qty_non_negative"),
        CheckConstraint("allocated_qty >= 0", name="check_allocated_qty_non_negative"),
        CheckConstraint("total_qty - reserved_qty - allocated_qty >= 0", name="check_available_qty_non_negative"),
    )


class Reservation(Base):
    """Reservation header (hold or allocation)."""
    __tablename__ = "reservations"
    
    reservation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_token = Column(Text, nullable=False, unique=True)  # Enforces idempotency
    user_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(SQLEnum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING)
    type = Column(SQLEnum(ReservationType), nullable=False)
    total_items = Column(Integer, nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    meta_data = Column("metadata", JSONB, nullable=True)  # Using "metadata" as column name, meta_data as attribute
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    items = relationship("ReservationItem", back_populates="reservation", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="reservation")
    
    __table_args__ = (
        CheckConstraint("total_items > 0", name="check_total_items_positive"),
    )


class ReservationItem(Base):
    """Line items for a reservation (supports batch atomicity)."""
    __tablename__ = "reservation_items"
    
    reservation_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey("reservations.reservation_id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.sku_id", ondelete="RESTRICT"), nullable=False)
    qty = Column(BigInteger, nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    reservation = relationship("Reservation", back_populates="items")
    sku = relationship("SKU", back_populates="reservation_items")
    
    __table_args__ = (
        CheckConstraint("qty > 0", name="check_qty_positive"),
        UniqueConstraint("reservation_id", "sku_id", name="uq_reservation_sku"),
    )


class InventorySnapshot(Base):
    """Periodic snapshots for reporting and consistency checks."""
    __tablename__ = "inventory_snapshots"
    
    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.sku_id"), nullable=False)
    snapshot_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    total_qty = Column(BigInteger, nullable=False)
    reserved_qty = Column(BigInteger, nullable=False)
    allocated_qty = Column(BigInteger, nullable=False)
    available_qty = Column(BigInteger, nullable=False)
    meta_data = Column("metadata", JSONB, nullable=True)  # Using "metadata" as column name, meta_data as attribute


class AuditLog(Base):
    """Append-only audit log for all inventory-changing operations."""
    __tablename__ = "audit_logs"
    
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey("reservations.reservation_id"), nullable=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.sku_id"), nullable=True)
    operation = Column(SQLEnum(AuditOperation), nullable=False)
    delta = Column(BigInteger, nullable=True)
    prev_total_qty = Column(BigInteger, nullable=True)
    new_total_qty = Column(BigInteger, nullable=True)
    prev_reserved_qty = Column(BigInteger, nullable=True)
    new_reserved_qty = Column(BigInteger, nullable=True)
    prev_allocated_qty = Column(BigInteger, nullable=True)
    new_allocated_qty = Column(BigInteger, nullable=True)
    actor = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta_data = Column("metadata", JSONB, nullable=True)  # Using "metadata" as column name, meta_data as attribute
    
    # Relationships
    reservation = relationship("Reservation", back_populates="audit_logs")

