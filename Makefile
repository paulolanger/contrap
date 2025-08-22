.PHONY: help setup update dev etl backend frontend all infra clean logs

help:
	@echo "Contrap - Multi-Service Orchestration"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup     - Initial setup: clone submodules and build images"
	@echo "  make update    - Update all submodules to latest"
	@echo "  make dev       - Start all services for development"
	@echo "  make infra     - Start only infrastructure (postgres, redis, pgadmin)"
	@echo "  make etl       - Run ETL service with infrastructure"
	@echo "  make backend   - Run backend service with infrastructure"
	@echo "  make frontend  - Run frontend with backend and infrastructure"
	@echo "  make clean     - Stop and remove all containers and volumes"
	@echo "  make logs      - Show logs for all running services"

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
	@echo "🚀 Starting all services..."
	docker-compose --profile etl --profile backend --profile frontend up

infra:
	@echo "🏗️  Starting infrastructure services..."
	docker-compose up postgres redis pgadmin

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
	docker-compose exec postgres pg_dump -U contrap_user contrap > backups/contrap_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created!"

db-restore:
	@echo "📥 Restoring database from backup..."
	@read -p "Enter backup filename: " backup; \
	docker-compose exec -T postgres psql -U contrap_user contrap < backups/$$backup
	@echo "✅ Database restored!"

# Service-specific operations
etl-shell:
	docker-compose exec etl /bin/bash

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
