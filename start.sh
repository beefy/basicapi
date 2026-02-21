#!/bin/bash

# Start script for running the FastAPI application

set -e

# Check if MongoDB is accessible
echo "Checking MongoDB connection..."
python -c "from pymongo import MongoClient; from app.core.config import settings; MongoClient(settings.mongodb_url).admin.command('ping'); print('MongoDB connection successful')"

# Run database migrations
echo "Running database migrations..."
python migrate.py up

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
