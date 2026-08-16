#!/bin/bash
set -e

echo "⏳ Waiting for PostgreSQL to be ready on $POSTGRES_SERVER:$POSTGRES_PORT..."
python3 -c '
import socket
import time
import os

host = os.getenv("POSTGRES_SERVER", "127.0.0.1")
port = int(os.getenv("POSTGRES_PORT", 5433))

for i in range(30):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"✓ PostgreSQL is reachable on {host}:{port}")
            break
    except OSError:
        time.sleep(1)
'

echo "🌱 Running HRMS Database Seeder..."
python3 seed_database.py || echo "⚠ Seeder finished or already initialized."

echo "🚀 Starting HRMS FastAPI Server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
