# Contrap - Portuguese Government Procurement Platform

This is the main orchestrator repository for the Contrap platform, which aggregates and analyzes Portuguese government procurement data.

## 🏗️ Architecture

Contrap is built as a microservices architecture with three main components:

- **[ETL Service](https://github.com/paulolanger/contrap-etl)** - Python-based data pipeline for fetching and processing government procurement data
- **[Backend API](https://github.com/paulolanger/contrap-backend)** - Node.js/GraphQL API server with Prisma ORM
- **[Frontend](https://github.com/paulolanger/contrap-frontend)** - Next.js web application with TypeScript and Tailwind CSS

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- Make (optional, but recommended)

### Setup

1. Clone this repository with submodules:
```bash
git clone --recursive https://github.com/paulolanger/contrap.git
cd contrap
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configurations
```

3. Build and start all services:
```bash
make setup  # Initial setup
make dev    # Start all services
```

## 📦 Available Commands

```bash
make help      # Show all available commands
make setup     # Initial setup and build
make dev       # Start all services
make infra     # Start only infrastructure (DB, Redis, PgAdmin)
make etl       # Run ETL service
make backend   # Run backend API
make frontend  # Run frontend application
make clean     # Stop and remove all containers
make logs      # Show logs for all services
```

## 🔧 Service URLs

When running locally, services are available at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:4000/graphql
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **PgAdmin**: http://localhost:5050

## 📂 Project Structure

```
contrap/
├── services/              # Git submodules for each service
│   ├── etl/              # ETL pipeline service
│   ├── backend/          # GraphQL API service
│   └── frontend/         # Next.js web application
├── database/             # Database schemas and migrations
├── docs/                 # Project documentation
├── scripts/              # Utility scripts
├── docker-compose.yml    # Docker orchestration
├── Makefile             # Development commands
└── .env.example         # Environment variables template
```

## 🔄 Working with Submodules

### Update all submodules to latest:
```bash
make update
# or
git submodule update --remote --merge
```

### Work on a specific service:
```bash
cd services/etl
# Make changes, commit, push
cd ../..
git add services/etl
git commit -m "Update ETL submodule"
```

## 🚢 Deployment

Each service can be deployed independently:

- **ETL**: Can be deployed as a scheduled job (Kubernetes CronJob, AWS Lambda, etc.)
- **Backend**: Deploy as a containerized service (ECS, Cloud Run, Kubernetes)
- **Frontend**: Deploy to Vercel, Netlify, or as a containerized service

## 📚 Documentation

- [System Requirements](REQUIREMENTS.md)
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [API Documentation](docs/api.md)
- [Database Schema](database/README.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For issues and questions, please open an issue in the respective service repository or contact the development team.
