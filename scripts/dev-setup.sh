#!/bin/bash

# Contrap Development Environment Setup Script
# This script sets up the development environment for the Contrap project

set -e  # Exit on error

echo "================================================"
echo "    Contrap Development Environment Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check for required tools
echo "Checking prerequisites..."

# Check Docker
if command -v docker >/dev/null 2>&1; then
    print_success "Docker is installed ($(docker --version))"
else
    print_error "Docker is not installed. Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check Docker Compose
if command -v docker-compose >/dev/null 2>&1; then
    print_success "Docker Compose is installed ($(docker-compose --version))"
else
    print_error "Docker Compose is not installed. It should come with Docker Desktop."
    exit 1
fi

# Check Python
if command -v python3.11 >/dev/null 2>&1; then
    print_success "Python 3.11 is installed ($(python3.11 --version))"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "$PYTHON_VERSION" == "3.11" ]] || [[ "$PYTHON_VERSION" > "3.11" ]]; then
        print_success "Python 3.11+ is installed ($(python3 --version))"
    else
        print_warning "Python 3.11+ is recommended (found $(python3 --version))"
    fi
else
    print_error "Python 3.11+ is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Check Node.js (optional for now, required later)
if command -v node >/dev/null 2>&1; then
    print_success "Node.js is installed ($(node --version))"
else
    print_warning "Node.js is not installed. It will be required for the backend API later."
fi

echo ""
echo "Setting up environment..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    print_success "Created .env file from .env.example"
    print_warning "Please update .env with your actual values"
else
    print_success ".env file already exists"
fi

# Create necessary directories
echo ""
echo "Creating project directories..."
mkdir -p data/{raw,processed,cache,archived}
mkdir -p database/init
mkdir -p logs
print_success "Project directories created"

# Start Docker services
echo ""
echo "Starting Docker services..."
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo ""
echo "Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker-compose exec -T postgres pg_isready -U contrap_user -d contrap >/dev/null 2>&1; then
        print_success "PostgreSQL is ready!"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        print_error "PostgreSQL failed to start. Please check Docker logs."
        exit 1
    fi
    
    echo -n "."
    sleep 2
done

# Check Redis
echo ""
echo "Checking Redis..."
if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    print_success "Redis is ready!"
else
    print_error "Redis is not responding. Please check Docker logs."
    exit 1
fi

echo ""
echo "================================================"
echo "    Development Environment Setup Complete!"
echo "================================================"
echo ""
echo "Services running:"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"
echo "  • PgAdmin: http://localhost:5050 (admin@contrap.pt / admin)"
echo ""
echo "Next steps:"
echo "  1. Initialize the database schema:"
echo "     psql -h localhost -U contrap_user -d contrap -f database/schema.sql"
echo ""
echo "  2. Set up Python virtual environment:"
echo "     cd etl && python3.11 -m venv venv && source venv/bin/activate"
echo "     pip install -r requirements.txt"
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f [service_name]"
echo ""
