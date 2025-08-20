#!/bin/bash

# ETL Pipeline Runner with Docker Environment
# This script ensures Docker services are running and runs the ETL pipeline

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ../.env ]; then
    print_warning ".env file not found. Creating from example..."
    cp ../.env.example ../.env
    print_status "Created .env file. Please update it with your configuration."
    
    # Set default Docker values
    cat > ../.env << EOF
# Database Configuration for Docker
DB_HOST=localhost
DB_PORT=5432
DB_NAME=contrap
DB_USER=contrap_user
DB_PASSWORD=contrap_dev_password

# API Configuration
API_BASE_URL=https://www.base.gov.pt/APIBase2
API_ACCESS_TOKEN=Nmq28lKgTbr05RaFOJNf

# Other configurations from .env.example
DATABASE_URL=postgresql://contrap_user:contrap_dev_password@localhost:5432/contrap
REDIS_URL=redis://localhost:6379
LOG_LEVEL=info
EOF
    print_status "Updated .env with Docker defaults"
fi

# Load environment variables
export $(grep -v '^#' ../.env | xargs)

# Check if Docker containers are running
print_status "Checking Docker containers..."

# Start containers if not running
if ! docker-compose -f ../docker-compose.yml ps | grep -q "contrap_postgres.*Up"; then
    print_warning "PostgreSQL container not running. Starting Docker services..."
    docker-compose -f ../docker-compose.yml up -d postgres redis
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose -f ../docker-compose.yml exec -T postgres pg_isready -U contrap_user -d contrap > /dev/null 2>&1; then
            print_status "PostgreSQL is ready!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
else
    print_status "PostgreSQL container is running"
fi

# Check if database schema exists
print_status "Checking database schema..."
if ! PGPASSWORD=$DB_PASSWORD psql -h localhost -U contrap_user -d contrap -c "\dt" 2>/dev/null | grep -q "announcements"; then
    print_warning "Database schema not found. Initializing..."
    
    # Find and run schema file
    if [ -f ../database/schema.sql ]; then
        PGPASSWORD=$DB_PASSWORD psql -h localhost -U contrap_user -d contrap -f ../database/schema.sql
        print_status "Database schema initialized"
    elif [ -f ../database/init/01_create_schema.sql ]; then
        PGPASSWORD=$DB_PASSWORD psql -h localhost -U contrap_user -d contrap -f ../database/init/01_create_schema.sql
        print_status "Database schema initialized"
    else
        print_error "Schema file not found. Looking for ../database/schema.sql or ../database/init/01_create_schema.sql"
        exit 1
    fi
else
    print_status "Database schema exists"
fi

# Check Python dependencies
if ! python -c "import asyncpg" 2>/dev/null; then
    print_warning "Python dependencies not installed. Installing..."
    pip install -r requirements.txt
fi

# Run the ETL pipeline with provided arguments
print_status "Starting ETL pipeline..."
echo "----------------------------------------"

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    python run_etl.py --help
    echo ""
    print_status "Quick examples:"
    echo "  $0 test                    # Test connections"
    echo "  $0 incremental             # Run current year update"
    echo "  $0 year 2023               # Process year 2023"
    echo "  $0 historical --start-year 2020 --end-year 2023  # Import historical data"
else
    # Run with provided arguments
    python run_etl.py "$@"
fi

# Show summary
echo "----------------------------------------"
print_status "ETL pipeline execution completed"

# Optional: Show database statistics
if [ "$1" != "test" ] && [ "$1" != "--help" ]; then
    print_status "Database statistics:"
    PGPASSWORD=$DB_PASSWORD psql -h localhost -U contrap_user -d contrap -t -c "
        SELECT 'Entities: ' || COUNT(*) FROM entities
        UNION ALL
        SELECT 'Announcements: ' || COUNT(*) FROM announcements
        UNION ALL
        SELECT 'Contracts: ' || COUNT(*) FROM contracts;
    " 2>/dev/null | grep -v "^$"
fi
