"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.database import init_db, close_db
from app.routers import inventory, skus
from app.config import settings
from app.services.inventory_service import InventoryService
from app.database import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    await init_db()
    
    # Start background task for expiry
    expiry_task = asyncio.create_task(expiry_worker())
    
    yield
    
    # Shutdown
    expiry_task.cancel()
    try:
        await expiry_task
    except asyncio.CancelledError:
        pass
    await close_db()


async def expiry_worker():
    """
    Background worker to expire held reservations.
    Runs periodically based on settings.
    """
    while True:
        try:
            await asyncio.sleep(settings.expiry_check_interval_seconds)
            
            async with AsyncSessionLocal() as db:
                service = InventoryService(db)
                count = await service.expire_holds()
                if count > 0:
                    print(f"Expired {count} reservation(s)")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in expiry worker: {e}")


app = FastAPI(
    title="Inventory Reservation Service",
    description="FastAPI service for inventory reservations with optimistic and pessimistic locking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(inventory.router)
app.include_router(skus.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Inventory Reservation Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

