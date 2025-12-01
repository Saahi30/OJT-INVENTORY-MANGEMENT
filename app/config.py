"""
Configuration management for the application.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Default database URL (can be overridden by .env file or environment variable)
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db"
    )
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database pool settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Expiry worker settings
    expiry_check_interval_seconds: int = 60
    
    # Locking strategy settings
    optimistic_max_retries: int = 3
    pessimistic_lock_timeout_seconds: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"
        # Don't fail if .env file doesn't exist
        env_file_required = False


# Load settings
# If .env file doesn't exist, it will use defaults or environment variables
settings = Settings()

# Print helpful message if using default database URL
if settings.database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db":
    print("⚠️  Using default database URL. To customize, create a .env file or set DATABASE_URL environment variable.")

