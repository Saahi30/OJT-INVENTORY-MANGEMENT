"""
Configuration management for the application.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Default database URL (can be overridden by .env file or environment variable)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db"
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
    
    @field_validator('database_url', mode='before')
    @classmethod
    def convert_database_url(cls, v):
        """
        Convert standard PostgreSQL URL to asyncpg format if needed.
        Render and other platforms provide postgresql:// but we need postgresql+asyncpg://
        """
        if isinstance(v, str):
            # If it's already in asyncpg format, return as is
            if v.startswith('postgresql+asyncpg://'):
                return v
            # If it's standard postgresql://, convert to asyncpg format
            if v.startswith('postgresql://'):
                return v.replace('postgresql://', 'postgresql+asyncpg://', 1)
            # If it's postgres:// (short form), convert to asyncpg format
            if v.startswith('postgres://'):
                return v.replace('postgres://', 'postgresql+asyncpg://', 1)
        return v
    
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
default_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db"
if settings.database_url == default_url:
    print("⚠️  Using default database URL. To customize, create a .env file or set DATABASE_URL environment variable.")

