# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Contrap** is a data intelligence platform that aggregates, processes, and delivers insights from Portuguese government bidding announcements and contracts. It's a SaaS application with a freemium newsletter service and advanced analytics features.

## Key Documentation

- **[REQUIREMENTS.md](REQUIREMENTS.md)** - Complete system specification, business model, and technical requirements
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Detailed 16-week implementation roadmap with code examples
- **[docs/async_api_implementation.md](docs/async_api_implementation.md)** - API retry logic and async handling

## Architecture

The project follows an ETL → Database → API → Frontend architecture:

1. **ETL Pipeline (Python)**: Fetches data from Portuguese Government API (`base.gov.pt`)
2. **Database (PostgreSQL)**: Stores normalized procurement data
3. **Backend (Node.js/GraphQL)**: Provides API for web application
4. **Frontend (Next.js)**: Web dashboard for users
5. **Newsletter Service**: Automated email notifications

For detailed architecture diagrams and technical specifications, see [REQUIREMENTS.md Section 2](REQUIREMENTS.md#2-system-architecture-overview)

## Project Structure

```
contrap/
├── data/
│   ├── raw/          # Raw JSON from government API
│   ├── processed/    # Chunked and normalized data
│   ├── cache/        # Temporary processing files
│   └── archived/     # Historical data backups
├── docs/
│   ├── async_api_implementation.md    # API retry logic documentation
│   ├── example_announcement.json      # Sample announcement data
│   ├── example_contract.json          # Sample contract data
│   └── example_entity.json            # Sample entity data
└── REQUIREMENTS.md                     # Comprehensive system requirements
```

## Key Development Commands

### ETL Pipeline Operations

```bash
# Fetch new announcements from API
python fetch_announcements.py

# Fetch new contracts from API  
python fetch_contracts.py

# Process raw data and load to database
python process_and_load.py

# Run full ETL pipeline
python etl_pipeline.py --full
```

### Database Operations

```bash
# Connect to PostgreSQL database
psql -U contrap -d contrap

# Run database migrations
python manage.py migrate

# Backup database
pg_dump -U contrap contrap > backup_$(date +%Y%m%d).sql

# Restore database
psql -U contrap contrap < backup_20250120.sql
```

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Run ETL in Docker
docker-compose run etl python fetch_announcements.py

# Access database in Docker
docker-compose exec postgres psql -U contrap -d contrap

# Stop all services
docker-compose down
```

### Newsletter Service

```bash
# Send daily digest manually
python send_daily_digest.py

# Send weekly summary
python send_weekly_summary.py

# Test email templates
python test_email_templates.py --template=daily
```

### Development Server

```bash
# Start backend API server
cd backend && npm run dev

# Start frontend Next.js app
cd frontend && npm run dev

# Run both with concurrently
npm run dev:all
```

### Testing

```bash
# Run Python ETL tests
pytest etl/tests/

# Run API tests
cd backend && npm test

# Run frontend tests
cd frontend && npm test

# Run integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Database Schema

The system uses a normalized 10-table structure with additional tables for user management and logging.

- **Core Tables**: entities, announcements, contracts
- **Lookup Tables**: contract_types, cpv_codes
- **Association Tables**: Many-to-many relationships for CPV codes, contract types, competitors

For complete schema details, see:
- [REQUIREMENTS.md Section 3.2](REQUIREMENTS.md#32-database-postgresql) - Database requirements
- [IMPLEMENTATION_PLAN.md Week 4](IMPLEMENTATION_PLAN.md#week-4-database-loader) - Complete SQL schema
- [IMPLEMENTATION_PLAN.md Week 6](IMPLEMENTATION_PLAN.md#week-6-testing--monitoring) - Data quality insights

## API Information

### Portuguese Government API
- Base URL: `https://www.base.gov.pt/APIBase2`
- Access Token: `Nmq28lKgTbr05RaFOJNf`
- Rate Limit: 5 requests/second
- Endpoints:
  - `/GetInfoContrato` - Contract information
  - `/GetInfoAnuncio` - Announcement information
  - `/GetInfoEntidades` - Entity information
  - `/GetInfoModContrat` - Contract modifications

### GraphQL API (Internal)
- Development: `http://localhost:4000/graphql`
- Production: `https://api.contrap.pt/graphql`

## Technology Stack

For the complete technology stack and dependencies, see:
- [REQUIREMENTS.md Section 8.1](REQUIREMENTS.md#81-development-stack) - Full stack details
- [IMPLEMENTATION_PLAN.md Phase 0](IMPLEMENTATION_PLAN.md#phase-0-foundation-setup-week-1) - Development environment setup

## Important Implementation Details

### Async API Handling
The Portuguese Government API can be very slow (2-5 minutes response times). The system implements:
- Extended timeouts (up to 60 minutes for batch operations)
- Exponential backoff retry logic
- Async request methods with configurable parameters

### Data Processing Pipeline

The ETL pipeline follows a multi-step process for data validation and normalization.

For detailed implementation, see:
- [IMPLEMENTATION_PLAN.md Phase 1](IMPLEMENTATION_PLAN.md#phase-1-etl-pipeline-core-weeks-2-4) - Complete ETL implementation with code
- [REQUIREMENTS.md Section 5](REQUIREMENTS.md#5-data-processing-requirements) - Data quality standards and retention policies

### Scheduled Jobs (Cron)
- Fetch announcements: Every 6 hours
- Fetch contracts: Every 6 hours (offset by 3 hours)
- Process and load: Every hour
- Daily newsletter: 8 AM daily
- Weekly summary: Monday 9 AM
- Database backup: 2 AM daily

## Environment Variables

Create a `.env` file based on `.env.example`. Required variables include database connections, API tokens, and service configurations.

For complete environment variable list, see:
- [REQUIREMENTS.md Section 8.2](REQUIREMENTS.md#82-environment-variables) - All required environment variables
- [IMPLEMENTATION_PLAN.md Phase 0](IMPLEMENTATION_PLAN.md#phase-0-foundation-setup-week-1) - Environment setup

## Common Development Tasks

### Add a New Data Field
1. Update database schema in migrations
2. Modify ETL processor to extract field
3. Update GraphQL schema
4. Add field to frontend components

### Debug Slow API Calls
1. Check `docs/async_api_implementation.md` for retry configuration
2. Increase timeout in AsyncRequestConfig
3. Monitor retry attempts in logs
4. Consider batch size reduction

### Process Historical Data
```bash
# Backfill specific year
python fetch_contracts.py --year=2024 --backfill

# Process archived data
python process_archived.py --input=data/archived/ --year=2024
```

## Key Files to Review

- `REQUIREMENTS.md` - Complete system specification
- `IMPLEMENTATION_PLAN.md` - Detailed implementation guide with code
- `docs/async_api_implementation.md` - API retry logic
- `docs/example_announcement.json` - Sample announcement data structure
- `docs/example_contract.json` - Sample contract data structure
- `docs/example_entity.json` - Sample entity data structure
- `data/processed/` - Processed JSON chunks

## API & Configuration Details

### GraphQL API
For the complete GraphQL schema, queries, and mutations, see:
- [REQUIREMENTS.md Section 3.3.1](REQUIREMENTS.md#331-graphql-api-nodejs--prisma) - GraphQL API specification
- [IMPLEMENTATION_PLAN.md Phase 3](IMPLEMENTATION_PLAN.md#phase-3-backend-api-development-weeks-7-9) - Complete API implementation with code

### Docker Configuration
For Docker Compose setup and service configuration, see:
- [REQUIREMENTS.md Section 3.5.1](REQUIREMENTS.md#351-docker-configuration) - Docker structure
- [IMPLEMENTATION_PLAN.md Phase 0](IMPLEMENTATION_PLAN.md#day-3-4-docker-infrastructure) - Docker setup

### API Rate Limits & Performance
For detailed performance requirements and rate limiting, see:
- [REQUIREMENTS.md Section 8.3](REQUIREMENTS.md#83-api-rate-limits) - Rate limit tiers
- [docs/async_api_implementation.md](docs/async_api_implementation.md) - Async handling and retry logic

## Notes

- The Portuguese Government API requires the `_AccessToken` header for all requests
- NIFs must be validated against Portuguese format rules
- CPV codes follow EU procurement vocabulary standards
- All dates from the API are in DD/MM/YYYY format and need conversion
- Contract competitors are stored as concatenated NIF strings that need parsing
- GDPR compliance required for user data handling
- Portuguese invoicing requirements (Faturação) must be integrated
