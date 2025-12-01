#!/bin/bash
# Simple script to run the FastAPI application

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

