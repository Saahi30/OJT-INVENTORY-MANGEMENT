"""
Core inventory service with optimistic and pessimistic locking strategies.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple, Union, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import asyncio
from app.models import (
    Inventory, Reservation, ReservationItem, ReservationStatus, 
    ReservationType, AuditLog, AuditOperation
)
from app.config import settings
from app.schemas import SKUItem


def reservation_to_dict(reservation: Reservation) -> Dict[str, Any]:
    """Convert Reservation ORM object to dict for Pydantic serialization."""
    return {
        "reservation_id": reservation.reservation_id,
        "client_token": reservation.client_token,
        "user_id": reservation.user_id,
        "status": reservation.status,
        "type": reservation.type,
        "total_items": reservation.total_items,
        "requested_at": reservation.requested_at,
        "expires_at": reservation.expires_at,
        "completed_at": reservation.completed_at,
        "metadata": reservation.meta_data,  # Map meta_data to metadata
        "items": [
            {
                "reservation_item_id": item.reservation_item_id,
                "sku_id": item.sku_id,
                "qty": item.qty,
                "unit_price": float(item.unit_price) if item.unit_price else None
            }
            for item in reservation.items
        ]
    }


class InventoryService:
    """Service for inventory operations with concurrency control."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._locks: dict[UUID, asyncio.Lock] = {}  # Per-SKU locks for pessimistic strategy
    
    def _get_lock(self, sku_id: UUID) -> asyncio.Lock:
        """Get or create lock for a SKU."""
        if sku_id not in self._locks:
            self._locks[sku_id] = asyncio.Lock()
        return self._locks[sku_id]
    
    async def _check_availability(
        self, 
        sku_id: UUID, 
        requested_qty: int,
        strategy: str = "optimistic"
    ) -> Tuple[bool, Optional[Inventory]]:
        """
        Check if sufficient inventory is available.
        Returns (is_available, inventory_record)
        """
        if strategy == "pessimistic":
            # Use FOR UPDATE to lock the row
            stmt = select(Inventory).where(Inventory.sku_id == sku_id).with_for_update()
        else:
            stmt = select(Inventory).where(Inventory.sku_id == sku_id)
        
        result = await self.db.execute(stmt)
        inventory = result.scalar_one_or_none()
        
        if not inventory:
            return False, None
        
        available = inventory.total_qty - inventory.reserved_qty - inventory.allocated_qty
        return available >= requested_qty, inventory
    
    async def _update_inventory_optimistic(
        self,
        sku_id: UUID,
        reserved_delta: int = 0,
        allocated_delta: int = 0,
        expected_version: int = None
    ) -> bool:
        """
        Update inventory using optimistic locking.
        Returns True if successful, False if version conflict.
        """
        if expected_version is None:
            # Read current version
            stmt = select(Inventory).where(Inventory.sku_id == sku_id)
            result = await self.db.execute(stmt)
            inventory = result.scalar_one_or_none()
            if not inventory:
                return False
            expected_version = inventory.version
        
        # Update with version check
        stmt = (
            update(Inventory)
            .where(
                Inventory.sku_id == sku_id,
                Inventory.version == expected_version
            )
            .values(
                reserved_qty=Inventory.reserved_qty + reserved_delta,
                allocated_qty=Inventory.allocated_qty + allocated_delta,
                version=Inventory.version + 1,
                updated_at=func.now()
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.flush()
        
        return result.rowcount == 1
    
    async def _update_inventory_pessimistic(
        self,
        sku_id: UUID,
        reserved_delta: int = 0,
        allocated_delta: int = 0
    ) -> bool:
        """
        Update inventory using pessimistic locking.
        Acquires lock before updating.
        """
        lock = self._get_lock(sku_id)
        
        try:
            await asyncio.wait_for(lock.acquire(), timeout=settings.pessimistic_lock_timeout_seconds)
        except asyncio.TimeoutError:
            return False
        
        try:
            # Lock the row in database
            stmt = select(Inventory).where(Inventory.sku_id == sku_id).with_for_update()
            result = await self.db.execute(stmt)
            inventory = result.scalar_one_or_none()
            
            if not inventory:
                return False
            
            # Check availability
            available = inventory.total_qty - inventory.reserved_qty - inventory.allocated_qty
            if reserved_delta > 0 and available < reserved_delta:
                return False
            if allocated_delta > 0 and (inventory.reserved_qty < allocated_delta):
                return False
            
            # Update
            inventory.reserved_qty += reserved_delta
            inventory.allocated_qty += allocated_delta
            inventory.version += 1
            inventory.updated_at = datetime.now(timezone.utc)
            
            await self.db.flush()
            return True
        finally:
            lock.release()
    
    async def create_hold(
        self,
        client_token: str,
        items: List[SKUItem],
        user_id: Optional[UUID],
        expires_in_seconds: int,
        strategy: str,
        metadata: Optional[dict] = None
    ) -> Tuple[Optional[Reservation], Optional[str]]:
        """
        Create a hold reservation.
        Returns (reservation, error_message)
        """
        # Check idempotency
        existing = await self.db.execute(
            select(Reservation)
            .where(Reservation.client_token == client_token)
            .options(selectinload(Reservation.items))
        )
        existing_reservation = existing.scalar_one_or_none()
        if existing_reservation:
            return reservation_to_dict(existing_reservation), None
        
        # Validate all SKUs have sufficient inventory
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        
        # Check availability for all items
        inventory_records = {}
        for item in items:
            is_available, inv = await self._check_availability(item.sku_id, item.qty, strategy)
            if not is_available:
                return None, f"Insufficient inventory for SKU {item.sku_id}"
            inventory_records[item.sku_id] = inv
        
        # Create reservation in transaction
        try:
            reservation = Reservation(
                client_token=client_token,
                user_id=user_id,
                status=ReservationStatus.PENDING,
                type=ReservationType.HOLD,
                total_items=len(items),
                expires_at=expires_at,
                meta_data=metadata
            )
            self.db.add(reservation)
            await self.db.flush()  # Get reservation_id
            
            # Create reservation items and update inventory
            for item in items:
                reservation_item = ReservationItem(
                    reservation_id=reservation.reservation_id,
                    sku_id=item.sku_id,
                    qty=item.qty
                )
                self.db.add(reservation_item)
                
                # Update inventory based on strategy
                if strategy == "optimistic":
                    success = False
                    for attempt in range(settings.optimistic_max_retries):
                        inv = inventory_records[item.sku_id]
                        success = await self._update_inventory_optimistic(
                            item.sku_id,
                            reserved_delta=item.qty,
                            expected_version=inv.version
                        )
                        if success:
                            break
                        # Re-read inventory for next attempt
                        _, inv = await self._check_availability(item.sku_id, item.qty, strategy)
                        inventory_records[item.sku_id] = inv
                    
                    if not success:
                        await self.db.rollback()
                        return None, f"Failed to reserve inventory for SKU {item.sku_id} after retries"
                else:  # pessimistic
                    success = await self._update_inventory_pessimistic(
                        item.sku_id,
                        reserved_delta=item.qty
                    )
                    if not success:
                        await self.db.rollback()
                        return None, f"Failed to reserve inventory for SKU {item.sku_id}"
                
                # Create audit log
                inv = inventory_records[item.sku_id]
                audit = AuditLog(
                    reservation_id=reservation.reservation_id,
                    sku_id=item.sku_id,
                    operation=AuditOperation.HOLD_CREATED,
                    delta=item.qty,
                    prev_reserved_qty=inv.reserved_qty - item.qty,
                    new_reserved_qty=inv.reserved_qty,
                    actor=user_id.hex if user_id else "system"
                )
                self.db.add(audit)
            
            reservation.status = ReservationStatus.HELD
            await self.db.commit()
            
            # Reload with items
            await self.db.refresh(reservation, ["items"])
            
            # Convert to dict to avoid lazy loading issues in Pydantic
            return reservation_to_dict(reservation), None
            
        except Exception as e:
            await self.db.rollback()
            return None, str(e)
    
    async def convert_hold_to_allocation(
        self,
        reservation_id: UUID
    ) -> Tuple[Optional[Reservation], Optional[str]]:
        """
        Convert a hold to allocation.
        Returns (reservation, error_message)
        """
        # Get reservation
        result = await self.db.execute(
            select(Reservation)
            .where(Reservation.reservation_id == reservation_id)
            .options(selectinload(Reservation.items))
        )
        reservation = result.scalar_one_or_none()
        
        if not reservation:
            return None, "Reservation not found"
        
        if reservation.status != ReservationStatus.HELD:
            return None, f"Reservation is not in HELD status (current: {reservation.status})"
        
        if reservation.expires_at and reservation.expires_at < datetime.utcnow():
            return None, "Reservation has expired"
        
        try:
            # Transfer reserved_qty to allocated_qty for each item
            for item in reservation.items:
                # Get current inventory
                stmt = select(Inventory).where(Inventory.sku_id == item.sku_id)
                result = await self.db.execute(stmt)
                inventory = result.scalar_one()
                
                # Update: decrease reserved, increase allocated
                inventory.reserved_qty -= item.qty
                inventory.allocated_qty += item.qty
                inventory.version += 1
                
                # Create audit log
                audit = AuditLog(
                    reservation_id=reservation.reservation_id,
                    sku_id=item.sku_id,
                    operation=AuditOperation.ALLOCATED,
                    delta=item.qty,
                    prev_reserved_qty=inventory.reserved_qty + item.qty,
                    new_reserved_qty=inventory.reserved_qty,
                    prev_allocated_qty=inventory.allocated_qty - item.qty,
                    new_allocated_qty=inventory.allocated_qty,
                    actor="system"
                )
                self.db.add(audit)
            
            reservation.status = ReservationStatus.ALLOCATED
            reservation.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            await self.db.refresh(reservation, ["items"])
            return reservation, None
            
        except Exception as e:
            await self.db.rollback()
            return None, str(e)
    
    async def release_hold(
        self,
        reservation_id: UUID
    ) -> Tuple[Optional[Reservation], Optional[str]]:
        """
        Release a hold, returning inventory to available.
        Returns (reservation, error_message)
        """
        # Get reservation
        result = await self.db.execute(
            select(Reservation)
            .where(Reservation.reservation_id == reservation_id)
            .options(selectinload(Reservation.items))
        )
        reservation = result.scalar_one_or_none()
        
        if not reservation:
            return None, "Reservation not found"
        
        if reservation.status != ReservationStatus.HELD:
            return None, f"Reservation is not in HELD status (current: {reservation.status})"
        
        try:
            # Decrease reserved_qty for each item
            for item in reservation.items:
                # Get current inventory
                stmt = select(Inventory).where(Inventory.sku_id == item.sku_id)
                result = await self.db.execute(stmt)
                inventory = result.scalar_one()
                
                # Update: decrease reserved
                inventory.reserved_qty -= item.qty
                inventory.version += 1
                
                # Create audit log
                audit = AuditLog(
                    reservation_id=reservation.reservation_id,
                    sku_id=item.sku_id,
                    operation=AuditOperation.HOLD_RELEASED,
                    delta=-item.qty,
                    prev_reserved_qty=inventory.reserved_qty + item.qty,
                    new_reserved_qty=inventory.reserved_qty,
                    actor="system"
                )
                self.db.add(audit)
            
            reservation.status = ReservationStatus.RELEASED
            reservation.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            await self.db.refresh(reservation, ["items"])
            return reservation_to_dict(reservation), None
            
        except Exception as e:
            await self.db.rollback()
            return None, str(e)
    
    async def expire_holds(self) -> int:
        """
        Expire all held reservations past their expiry time.
        Returns count of expired reservations.
        """
        now = datetime.now(timezone.utc)
        
        # Find expired holds
        result = await self.db.execute(
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.HELD,
                Reservation.expires_at <= now
            )
            .options(selectinload(Reservation.items))
        )
        expired_reservations = result.scalars().all()
        
        count = 0
        for reservation in expired_reservations:
            try:
                # Decrease reserved_qty for each item
                for item in reservation.items:
                    stmt = select(Inventory).where(Inventory.sku_id == item.sku_id)
                    inv_result = await self.db.execute(stmt)
                    inventory = inv_result.scalar_one()
                    
                    inventory.reserved_qty -= item.qty
                    inventory.version += 1
                    
                    # Create audit log
                    audit = AuditLog(
                        reservation_id=reservation.reservation_id,
                        sku_id=item.sku_id,
                        operation=AuditOperation.EXPIRED,
                        delta=-item.qty,
                        prev_reserved_qty=inventory.reserved_qty + item.qty,
                        new_reserved_qty=inventory.reserved_qty,
                        actor="expiry_worker"
                    )
                    self.db.add(audit)
                
                reservation.status = ReservationStatus.EXPIRED
                reservation.completed_at = now
                count += 1
                
            except Exception as e:
                # Log error but continue with other reservations
                print(f"Error expiring reservation {reservation.reservation_id}: {e}")
                continue
        
        if count > 0:
            await self.db.commit()
        
        return count
    
    async def get_availability(self, sku_ids: Optional[List[UUID]] = None) -> List[dict]:
        """
        Get availability snapshot for SKU(s).
        """
        if sku_ids:
            stmt = select(Inventory).where(Inventory.sku_id.in_(sku_ids))
        else:
            stmt = select(Inventory)
        
        result = await self.db.execute(stmt)
        inventories = result.scalars().all()
        
        return [
            {
                "sku_id": inv.sku_id,
                "total_qty": inv.total_qty,
                "reserved_qty": inv.reserved_qty,
                "allocated_qty": inv.allocated_qty,
                "available_qty": inv.total_qty - inv.reserved_qty - inv.allocated_qty,
                "version": inv.version
            }
            for inv in inventories
        ]
    
    async def check_consistency(self) -> dict:
        """
        Check inventory consistency across all SKUs.
        Returns consistency report.
        """
        stmt = select(Inventory)
        result = await self.db.execute(stmt)
        inventories = result.scalars().all()
        
        inconsistent = []
        for inv in inventories:
            calculated_available = inv.total_qty - inv.reserved_qty - inv.allocated_qty
            stored_available = inv.total_qty - inv.reserved_qty - inv.allocated_qty
            
            # Check for negative values or mismatches
            if calculated_available < 0:
                inconsistent.append({
                    "sku_id": str(inv.sku_id),
                    "issue": "negative_available",
                    "calculated_available": calculated_available,
                    "total_qty": inv.total_qty,
                    "reserved_qty": inv.reserved_qty,
                    "allocated_qty": inv.allocated_qty
                })
        
        return {
            "is_consistent": len(inconsistent) == 0,
            "total_skus": len(inventories),
            "inconsistent_skus": inconsistent,
            "timestamp": datetime.now(timezone.utc)
        }

