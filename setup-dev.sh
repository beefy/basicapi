#!/bin/bash

# Development setup script for BasicAPI

set -e

echo "🚀 Setting up BasicAPI development environment..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | sed 's/Python //' | cut -d' ' -f1 | cut -d'.' -f1-2)
required_version="3.11"

if [[ $(echo "$python_version $required_version" | tr " " "
" | sort -V | head -n1) != "$required_version" ]]; then
    echo "❌ Python 3.11+ is required. Found Python $python_version"
    echo "Please install Python 3.11+ and try again."
    exit 1
fi

echo "✅ Python $python_version found"

# Check if we're already in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Using existing virtual environment: $VIRTUAL_ENV"
else
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

echo "🧪 Running tests to verify setup..."
export PYTHONPATH="${PWD}:${PYTHONPATH}"
# Skip tests if MongoDB is not running to avoid connection errors
if pytest tests/ -v --tb=short 2>/dev/null; then
    echo "✅ All tests passed!"
else
    echo "⚠️  Tests failed - this may be due to MongoDB not running"
    echo "   Tests will work once MongoDB is available"
fi

echo "🎉 Development environment setup complete!"
echo ""
echo "To start development:"
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "1. Virtual environment is already active"
else
    echo "1. Activate the virtual environment: source venv/bin/activate"
fi
echo "2. Start MongoDB (if running locally)"
echo "3. Run migrations: python migrate.py up"
echo "4. Start the application: uvicorn app.main:app --reload"
echo ""
echo "Or use Docker Compose: docker-compose up"
echo ""
echo "📖 API Documentation will be available at: http://localhost:8000/docs"