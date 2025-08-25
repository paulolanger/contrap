.PHONY: help setup update dev dev-logs dev-stop etl backend frontend all infra clean logs

help:
	@echo "Contrap - Multi-Service Orchestration"
	@echo ""
	@echo "🚀 Service Management:"
	@echo "  make setup              - Initial setup: clone submodules and build images"
	@echo "  make dev                - Start ALL services (postgres, redis, etl, backend, frontend)"
	@echo "  make dev-logs           - Show logs for all services"
	@echo "  make dev-stop           - Stop all services"
	@echo "  make infra              - Start only infrastructure (postgres, redis)"
	@echo "  make clean              - Stop and remove all containers and volumes"
	@echo "  make ps                 - Show status of all services"
	@echo ""
	@echo "⚙️  ETL Pipeline Commands:"
	@echo "  make etl-incremental    - Run incremental update for current year"
	@echo "  make etl-year year=2024 - Run ETL for specific year"
	@echo "  make etl-historical start=2020 end=2023 - Run historical import"
	@echo "  make etl-announcements  - Fetch announcements only"
	@echo "  make etl-contracts      - Fetch contracts only"
	@echo "  make etl-entities       - Fetch entities only"
	@echo "  make etl-test           - Test API and database connections"
	@echo "  make etl-run cmd='...'  - Run custom ETL command"
	@echo "  make etl-shell          - Open shell in ETL container"
	@echo "  make etl-migrate        - Run database migrations"
	@echo ""
	@echo "💾 Database Operations:"
	@echo "  make db-shell           - Connect to PostgreSQL CLI"
	@echo "  make db-backup          - Create database backup"
	@echo "  make db-restore         - Restore database from backup"
	@echo "  make db-migrate         - Run database migrations"
	@echo "  make db-reset           - Drop and recreate database (WARNING!)"
	@echo ""
	@echo "📋 Examples:"
	@echo "  make etl-run cmd='incremental --verbose'           # Verbose incremental update"
	@echo "  make etl-run cmd='year 2024 --no-cache'            # Year 2024 without cache"
	@echo "  make etl-year year=2024 args='--verbose --no-cache' # Year with extra args"

setup:
	@echo "🚀 Setting up Contrap..."
	git submodule update --init --recursive
	cp -n .env.example .env || true
	docker-compose build
	@echo "✅ Setup complete!"

update:
	@echo "📦 Updating all submodules..."
	git submodule update --remote --merge
	@echo "✅ Submodules updated!"

dev:
	@echo "🚀 Starting all services (postgres, redis, etl, backend, frontend)..."
	docker-compose --profile etl --profile backend --profile frontend up -d
	@echo "✅ All services started! Check status with 'make ps'"
	@echo "📊 View logs with 'make dev-logs' or 'docker-compose logs -f [service_name]'"

dev-logs:
	@echo "📊 Showing logs for all services (Ctrl+C to exit)..."
	docker-compose --profile etl --profile backend --profile frontend logs -f

dev-stop:
	@echo "🛑 Stopping all services..."
	docker-compose --profile etl --profile backend --profile frontend down
	@echo "✅ All services stopped!"

infra:
	@echo "🏗️  Starting infrastructure services..."
	docker-compose up -d postgres redis

etl:
	@echo "⚙️  Starting ETL pipeline..."
	docker-compose --profile etl up

backend:
	@echo "🔧 Starting backend API..."
	docker-compose --profile backend up

frontend:
	@echo "🎨 Starting frontend application..."
	docker-compose --profile backend --profile frontend up

all: dev

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	@echo "✅ Cleanup complete!"

logs:
	docker-compose logs -f

# Database operations
db-shell:
	docker-compose exec postgres psql -U contrap_user -d contrap

db-backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U contrap_user contrap > backups/contrap_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created!"

db-restore:
	@echo "📥 Restoring database from backup..."
	@read -p "Enter backup filename: " backup; \
	docker-compose exec -T postgres psql -U contrap_user contrap < backups/$$backup
	@echo "✅ Database restored!"

db-migrate:
	@echo "🆙 Running database migrations..."
	docker exec contrap_etl /entrypoint.sh migrate
	@echo "✅ Migrations completed!"

db-reset:
	@echo "⚠️  WARNING: This will drop and recreate the database!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose exec postgres psql -U contrap_user -d postgres -c "DROP DATABASE IF EXISTS contrap;"; \
		docker-compose exec postgres psql -U contrap_user -d postgres -c "CREATE DATABASE contrap;"; \
		docker exec contrap_etl /entrypoint.sh migrate; \
		echo "✅ Database reset complete!"; \
	else \
		echo "🚫 Operation cancelled"; \
	fi

db-init-test:
	@echo "🧪 Testing database connection..."
	docker exec contrap_etl /entrypoint.sh test

# ETL Pipeline Operations
# Usage examples:
#   make etl-run cmd="incremental"                     # Run incremental update
#   make etl-run cmd="year 2023"                       # Run for specific year
#   make etl-run cmd="historical 2020 2023"            # Run historical import
#   make etl-run cmd="test"                            # Test connections
#   make etl-run cmd="incremental --no-cache"          # Run without cache
#   make etl-run cmd="year 2024 --verbose"             # Run with verbose logging

etl-run:
	@echo "⚙️  Running ETL command: $(cmd)"
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py $(cmd)"

# Convenience ETL commands
etl-incremental:
	@echo "📦 Running incremental ETL update for current year..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental"

etl-incremental-verbose:
	@echo "📦 Running incremental ETL update with verbose logging..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental --verbose"

etl-incremental-nocache:
	@echo "📦 Running incremental ETL update without cache..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental --no-cache"

etl-year:
	@if [ -z "$(year)" ]; then \
		echo "❌ Please specify a year: make etl-year year=2024"; \
		exit 1; \
	fi
	@echo "📅 Running ETL for year $(year)..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py year $(year) $(args)"

etl-historical:
	@if [ -z "$(start)" ] || [ -z "$(end)" ]; then \
		echo "❌ Please specify start and end years: make etl-historical start=2020 end=2023"; \
		exit 1; \
	fi
	@echo "📚 Running historical ETL from $(start) to $(end)..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py historical $(start) $(end) $(args)"

etl-test:
	@echo "🧪 Testing ETL connections (API and Database)..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py test"

# ETL with specific data types
etl-announcements:
	@echo "📢 Fetching announcements only..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental --data-types announcements"

etl-contracts:
	@echo "📄 Fetching contracts only..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental --data-types contracts"

etl-entities:
	@echo "🏢 Fetching entities only..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental --data-types entities"

etl-modifications:
	@echo "✏️  Fetching contract modifications only..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python run_etl.py incremental --data-types modifications"

# ETL maintenance commands
etl-shell:
	@echo "🐚 Opening shell in ETL container..."
	@docker compose --profile etl run --rm --entrypoint bash etl

etl-logs:
	@echo "📊 Showing ETL logs..."
	@docker compose logs -f etl

etl-restart:
	@echo "🔄 Restarting ETL service..."
	@docker compose --profile etl restart etl

# Run migrations through ETL service
etl-migrate:
	@echo "🆙 Running database migrations through ETL service..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "python migrate.py"

# Run Alembic migrations (if alembic is installed)
etl-alembic:
	@echo "🆙 Running Alembic migrations..."
	@docker compose --profile etl run --rm --entrypoint bash etl -c "pip install alembic && alembic upgrade head"

# Service-specific operations

backend-shell:
	docker-compose exec backend /bin/sh

frontend-shell:
	docker-compose exec frontend /bin/sh

# Development helpers
ps:
	docker-compose ps

restart:
	docker-compose restart $(service)

rebuild:
	docker-compose build --no-cache $(service)
