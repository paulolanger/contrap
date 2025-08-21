#!/bin/bash

# Docker ETL Runner
# Runs the ETL pipeline using Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_command() {
    echo -e "${BLUE}[RUNNING]${NC} $1"
}

# Check if we're in the etl directory
if [ ! -f "run_etl.py" ]; then
    print_error "Please run this script from the etl directory"
    exit 1
fi

# Build the ETL Docker image
print_status "Building ETL Docker image..."
docker build -t contrap-etl:latest .

# Check if database is running
print_status "Checking database container..."
if ! docker ps | grep -q contrap_postgres; then
    print_warning "Database not running. Starting containers..."
    cd ..
    docker-compose up -d postgres redis
    cd etl
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker run --rm \
            --network contrap_contrap_network \
            postgres:15-alpine \
            pg_isready -h postgres -U contrap_user -d contrap > /dev/null 2>&1; then
            print_status "Database is ready!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
fi

# Initialize database schema if needed
print_status "Checking database schema..."
SCHEMA_CHECK=$(docker run --rm \
    --network contrap_contrap_network \
    -e PGPASSWORD=contrap_dev_password \
    postgres:15-alpine \
    psql -h postgres -U contrap_user -d contrap -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'announcements';" 2>/dev/null | tr -d ' ')

if [ "$SCHEMA_CHECK" = "0" ] || [ -z "$SCHEMA_CHECK" ]; then
    print_warning "Database schema not found. Initializing..."
    docker run --rm \
        --network contrap_contrap_network \
        -e PGPASSWORD=contrap_dev_password \
        -v "$(pwd)/../database/schema_en.sql:/tmp/schema.sql:ro" \
        postgres:15-alpine \
        psql -h postgres -U contrap_user -d contrap -f /tmp/schema.sql
    print_status "Database schema initialized"
else
    print_status "Database schema exists"
fi

# Run ETL command
if [ $# -eq 0 ]; then
    # No arguments - show help
    print_status "Running ETL help..."
    docker run --rm \
        --network contrap_contrap_network \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e DB_HOST=postgres \
        -e DB_PORT=5432 \
        -e DB_NAME=contrap \
        -e DB_USER=contrap_user \
        -e DB_PASSWORD=contrap_dev_password \
        -e API_BASE_URL=https://www.base.gov.pt/APIBase2 \
        -e API_ACCESS_TOKEN=Nmq28lKgTbr05RaFOJNf \
        contrap-etl:latest --help
    
    echo ""
    print_status "Examples:"
    echo "  $0 test                                      # Test connections"
    echo "  $0 incremental                               # Run incremental update"
    echo "  $0 year 2024                                 # Process year 2024"
    echo "  $0 year 2024 --data-types announcements     # Process only announcements"
    echo "  $0 historical --start-year 2020 --end-year 2023  # Historical import"
else
    # Run with provided arguments
    print_command "docker run etl $*"
    docker run --rm -it \
        --network contrap_contrap_network \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e DB_HOST=postgres \
        -e DB_PORT=5432 \
        -e DB_NAME=contrap \
        -e DB_USER=contrap_user \
        -e DB_PASSWORD=contrap_dev_password \
        -e API_BASE_URL=https://www.base.gov.pt/APIBase2 \
        -e API_ACCESS_TOKEN=Nmq28lKgTbr05RaFOJNf \
        -e LOG_LEVEL=INFO \
        contrap-etl:latest "$@"
    
    # Show database statistics after run
    if [ "$1" != "test" ] && [ "$1" != "--help" ]; then
        echo ""
        print_status "Database statistics:"
        docker run --rm \
            --network contrap_contrap_network \
            -e PGPASSWORD=contrap_dev_password \
            postgres:15-alpine \
            psql -h postgres -U contrap_user -d contrap -t -c "
                SELECT 'Entities: ' || COUNT(*) FROM entities
                UNION ALL
                SELECT 'Announcements: ' || COUNT(*) FROM announcements
                UNION ALL
                SELECT 'Contracts: ' || COUNT(*) FROM contracts
                UNION ALL
                SELECT 'Modifications: ' || COUNT(*) FROM contract_modifications;
            " 2>/dev/null | grep -v "^$"
    fi
fi
