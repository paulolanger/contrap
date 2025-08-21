# ETL Pipeline Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy ETL source code
COPY src/ ./src/
COPY run_etl.py .

# Create necessary directories
RUN mkdir -p /app/data/raw/announcements \
             /app/data/raw/contracts \
             /app/data/raw/modifications \
             /app/data/raw/entities \
             /app/data/validated \
             /app/data/processed \
             /app/data/errors \
             /app/data/reports \
             /app/logs

# Set environment variables defaults
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DB_HOST=postgres \
    DB_PORT=5432 \
    DB_NAME=contrap \
    DB_USER=contrap_user \
    DB_PASSWORD=contrap_dev_password

# Make the script executable
RUN chmod +x run_etl.py

# Default command
ENTRYPOINT ["python", "run_etl.py"]
CMD ["--help"]
