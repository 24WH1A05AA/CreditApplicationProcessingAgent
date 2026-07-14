#!/bin/bash
set -e

echo "Starting Credit Processing Backend..."

# Create database and uploads folders
mkdir -p /app/data /app/uploads /app/data/chromadb /app/data/debug_traces

# Optional: Run Alembic database migrations if present
# if [ -f "alembic.ini" ]; then
#     echo "Running database migrations..."
#     alembic upgrade head
# fi

# Start uvicorn server
echo "Launching FastAPI Application Server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
