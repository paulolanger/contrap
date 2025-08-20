# ETL Pipeline with Docker

## Overview

The `run_etl.py` script performs the complete ETL process:
1. **Fetches** data from the Portuguese Government API
2. **Validates** and cleans the data
3. **Processes** and transforms the data
4. **Inserts** data into the PostgreSQL database

## Database Operations

Yes, the ETL pipeline **DOES** insert data into the database. It:
- Creates/updates entities (organizations)
- Inserts announcements
- Inserts contracts
- Links CPV codes
- Manages relationships between tables

## Running with Docker

### Prerequisites

1. **Start Docker services:**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- PgAdmin interface (port 5050)

### Configuration

2. **Create `.env` file in the project root:**
```bash
cp .env.example .env
```

3. **Update `.env` with Docker database credentials:**
```env
# Database Configuration for Docker
DB_HOST=localhost
DB_PORT=5432
DB_NAME=contrap
DB_USER=contrap_user
DB_PASSWORD=contrap_dev_password  # Match docker-compose.yml

# API Configuration
API_BASE_URL=https://www.base.gov.pt/APIBase2
API_ACCESS_TOKEN=Nmq28lKgTbr05RaFOJNf
```

### Running the ETL Pipeline

4. **Install Python dependencies:**
```bash
pip install -r etl/requirements.txt
```

5. **Initialize the database schema (if not already done):**
```bash
psql -h localhost -U contrap_user -d contrap -f database/schema.sql
```

6. **Test connections first:**
```bash
./etl/run_etl.py test
```

This verifies:
- API connectivity
- Database connectivity
- Configuration validity

7. **Run ETL operations:**

**Incremental update (current year):**
```bash
./etl/run_etl.py incremental
```

**Process specific year:**
```bash
./etl/run_etl.py year 2023
```

**Historical import:**
```bash
./etl/run_etl.py historical --start-year 2020 --end-year 2023
```

### Docker Network Considerations

When running the ETL script **from your host machine** (outside Docker):
- Use `localhost` as DB_HOST
- Use port `5432` (mapped from Docker)

If you want to run the ETL **inside a Docker container**, you would need to:
- Use `postgres` as DB_HOST (Docker service name)
- Be on the same Docker network (`contrap_network`)

### Alternative: Run ETL in Docker Container

To run the ETL pipeline inside Docker, create this Dockerfile:

```dockerfile
# etl/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ETL code
COPY . .

# Make script executable
RUN chmod +x run_etl.py

ENTRYPOINT ["python", "run_etl.py"]
```

Then add to `docker-compose.yml`:

```yaml
  etl:
    build: ./etl
    container_name: contrap_etl
    environment:
      DB_HOST: postgres  # Use Docker service name
      DB_PORT: 5432
      DB_NAME: contrap
      DB_USER: contrap_user
      DB_PASSWORD: ${DB_PASSWORD:-contrap_dev_password}
      API_BASE_URL: https://www.base.gov.pt/APIBase2
      API_ACCESS_TOKEN: Nmq28lKgTbr05RaFOJNf
    volumes:
      - ./data:/app/data  # Mount data directory
      - ./logs:/app/logs  # Mount logs directory
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - contrap_network
```

Run with:
```bash
docker-compose run etl incremental
docker-compose run etl year 2023
docker-compose run etl historical --start-year 2020 --end-year 2023
```

## Monitoring

### View logs:
```bash
tail -f logs/etl_pipeline_*.log
```

### Check database:
```bash
# Via psql
psql -h localhost -U contrap_user -d contrap

# Via PgAdmin
# Open http://localhost:5050
# Login: admin@contrap.pt / admin (or your PGADMIN_PASSWORD)
```

### Database queries to verify data:
```sql
-- Check imported data counts
SELECT 'entities' as table_name, COUNT(*) as count FROM entities
UNION ALL
SELECT 'announcements', COUNT(*) FROM announcements
UNION ALL
SELECT 'contracts', COUNT(*) FROM contracts;

-- Recent imports
SELECT DATE(created_at) as import_date, 
       COUNT(*) as records 
FROM announcements 
GROUP BY DATE(created_at) 
ORDER BY import_date DESC 
LIMIT 10;
```

## Troubleshooting

### Connection refused error:
- Ensure Docker containers are running: `docker-compose ps`
- Check if PostgreSQL is healthy: `docker-compose ps postgres`
- Verify port 5432 is not already in use: `lsof -i :5432`

### Authentication failed:
- Check `.env` file has correct credentials
- Verify credentials match `docker-compose.yml`
- Try connecting directly: `psql -h localhost -U contrap_user -d contrap`

### No data imported:
- Check API is accessible: `curl https://www.base.gov.pt/APIBase2/announcements?year=2024`
- Review logs: `tail -f logs/etl_pipeline_*.log`
- Verify data directory permissions: `ls -la data/`

## Performance Tips

1. **For large historical imports:**
   - Run year by year to avoid overwhelming the API
   - Use the cache to avoid re-fetching data
   - Monitor memory usage with `docker stats`

2. **Database optimization:**
   - Ensure indexes are created (check `01_create_schema.sql`)
   - Run `VACUUM ANALYZE` after large imports
   - Monitor with `pg_stat_activity`

3. **Rate limiting:**
   - The ETL respects API rate limits automatically
   - Default delay between requests: 0.5 seconds
   - Adjust in `etl/src/config.py` if needed
