#!/bin/bash

set -e

echo "==================================="
echo "RAG Server Installation Script"
echo "==================================="

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Using default values."
fi

# Check if PostgreSQL client is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL client not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y postgresql-client
fi

# Test database connection
echo "Testing database connection..."
export PGPASSWORD=$POSTGRES_PASSWORD
if psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1" > /dev/null 2>&1; then
    echo "✓ Database connection successful"
else
    echo "✗ Database connection failed. Please check your database credentials and ensure the database server is running."
    exit 1
fi

# Check if pgvector extension is available
echo "Checking for pgvector extension..."
if psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT * FROM pg_available_extensions WHERE name='vector'" | grep -q vector; then
    echo "✓ pgvector extension is available"
else
    echo "✗ pgvector extension is not available on the database server."
    echo "Please install pgvector on your PostgreSQL server:"
    echo "  https://github.com/pgvector/pgvector"
    exit 1
fi

# Initialize database schema
echo "Initializing database schema..."
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f init.sql
echo "✓ Database schema initialized"

# Install Python dependencies in virtual environment
echo "Installing Python dependencies..."
if command -v python3 &> /dev/null; then
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    echo "✓ Python dependencies installed in virtual environment"
else
    echo "✗ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Build Docker image
echo "Building Docker image..."
# Stop and remove existing container if running
if docker ps -a --format '{{.Names}}' | grep -q '^rag-server$'; then
    echo "Stopping and removing existing container..."
    docker stop rag-server 2>/dev/null || true
    docker rm rag-server 2>/dev/null || true
fi
docker build -t rag-server:latest .
echo "✓ Docker image built successfully"

echo ""
echo "==================================="
echo "Installation completed successfully!"
echo "==================================="
echo ""
echo "To run the server locally:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "To run the server in Docker:"
echo "  docker run -d -p 8000:8000 --env-file .env --name rag-server rag-server:latest"
echo ""
echo "API Documentation will be available at:"
echo "  http://localhost:8000/docs"
echo ""
