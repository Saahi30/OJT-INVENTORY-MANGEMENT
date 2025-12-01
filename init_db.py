#!/usr/bin/env python3
"""
Initialize database tables.
Run this once after deployment to create all tables.
"""
import asyncio
from app.database import init_db

if __name__ == "__main__":
    print("Initializing database...")
    asyncio.run(init_db())
    print("Database initialized successfully!")

