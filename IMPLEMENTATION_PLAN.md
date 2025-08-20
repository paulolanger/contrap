# Contrap Technical Implementation Plan
## Detailed Step-by-Step Development Guide

---

## Overview
This document provides a comprehensive, step-by-step implementation plan for building the Contrap platform from scratch. Each phase includes specific tasks, acceptance criteria, and technical details.

## Timeline: 16 Weeks Total
- **Phase 0**: Foundation Setup (Week 1)
- **Phase 1**: ETL Pipeline Core (Weeks 2-4)
- **Phase 2**: Database & Data Processing (Weeks 5-6)
- **Phase 3**: Backend API Development (Weeks 7-9)
- **Phase 4**: Frontend Application (Weeks 10-12)
- **Phase 5**: Newsletter System (Week 13)
- **Phase 6**: Testing & Deployment (Weeks 14-15)
- **Phase 7**: Launch & Monitoring (Week 16)

---

## Phase 0: Foundation Setup (Week 1)

### Day 1-2: Development Environment

#### 1.1 Initialize Project Structure
```bash
mkdir -p contrap/{etl,backend,frontend,database,docker,scripts,tests}
cd contrap
git init
```

#### 1.2 Create Base Configuration Files
- [ ] Create `.gitignore` with Python, Node.js, and IDE patterns
- [ ] Create `.env.example` with all required environment variables
- [ ] Create `README.md` with project overview
- [ ] Copy `REQUIREMENTS.md`, `WARP.md`, and docs folder

#### 1.3 Setup Python Environment
```bash
cd etl
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

Create `requirements.txt`:
```txt
aiohttp==3.9.0
pandas==2.1.0
sqlalchemy==2.0.0
asyncio-throttle==1.0.2
python-dotenv==1.0.0
schedule==1.2.0
psycopg2-binary==2.9.0
pydantic==2.0.0
pytest==7.4.0
pytest-asyncio==0.21.0
black==23.0.0
flake8==6.0.0
```

### Day 3-4: Docker Infrastructure

#### 1.4 Create Docker Compose Configuration
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: contrap_postgres
    environment:
      POSTGRES_DB: contrap
      POSTGRES_USER: contrap_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U contrap_user -d contrap"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: contrap_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: contrap_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@contrap.pt
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

#### 1.5 Create Development Scripts
Create `scripts/dev-setup.sh`:
```bash
#!/bin/bash
# Development environment setup script

echo "Setting up Contrap development environment..."

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "Docker required but not installed."; exit 1; }
command -v python3.11 >/dev/null 2>&1 || { echo "Python 3.11 required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js required but not installed."; exit 1; }

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please update with your values"
fi

# Start Docker services
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

echo "Development environment setup complete!"
```

### Day 5: Version Control & CI/CD

#### 1.6 Setup GitHub Repository
- [ ] Create GitHub repository
- [ ] Add branch protection rules for main branch
- [ ] Setup GitHub Actions workflow

Create `.github/workflows/ci.yml`:
```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-etl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd etl
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd etl
          pytest tests/

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd backend
          npm ci
      - name: Run tests
        run: |
          cd backend
          npm test
```

---

## Phase 1: ETL Pipeline Core (Weeks 2-4)

### Week 2: API Client Implementation

#### 2.1 Create Base API Client
Create `etl/src/api_client.py`:
```python
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from asyncio_throttle import Throttler

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    base_url: str = "https://www.base.gov.pt/APIBase2"
    access_token: str = "Nmq28lKgTbr05RaFOJNf"
    rate_limit: int = 5  # requests per second
    timeout: int = 300  # seconds
    max_retries: int = 3
    retry_delay: int = 2

class ContrapAPIClient:
    def __init__(self, config: APIConfig):
        self.config = config
        self.throttler = Throttler(rate_limit=config.rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make an API request with retry logic and rate limiting"""
        url = f"{self.config.base_url}/{endpoint}"
        headers = {"_AccessToken": self.config.access_token}
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.throttler:
                    async with self.session.get(
                        url, 
                        headers=headers, 
                        params=params
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {endpoint}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    raise
    
    async def get_announcements(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch announcements for a date range"""
        params = {
            "dataInicio": start_date.strftime("%Y-%m-%d"),
            "dataFim": end_date.strftime("%Y-%m-%d")
        }
        
        result = await self._make_request("GetInfoAnuncio", params)
        return result.get("items", [])
    
    async def get_contracts(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch contracts for a date range"""
        params = {
            "dataInicio": start_date.strftime("%Y-%m-%d"),
            "dataFim": end_date.strftime("%Y-%m-%d")
        }
        
        result = await self._make_request("GetInfoContrato", params)
        return result.get("items", [])
    
    async def get_entity(self, nif: str) -> Dict[str, Any]:
        """Fetch entity information by NIF"""
        params = {"nifEntidade": nif}
        return await self._make_request("GetInfoEntidades", params)
```

#### 2.2 Create Data Fetcher
Create `etl/src/fetcher.py`:
```python
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging

from api_client import ContrapAPIClient, APIConfig

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self, output_dir: Path = Path("data/raw")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_config = APIConfig()
        
    def _save_to_file(self, data: List[Dict], data_type: str, date: datetime):
        """Save fetched data to JSON file"""
        filename = f"{data_type}_{date.strftime('%Y%m%d')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(data)} {data_type} to {filepath}")
        return filepath
    
    async def fetch_daily_announcements(self, date: datetime = None):
        """Fetch announcements for a specific day"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        async with ContrapAPIClient(self.api_config) as client:
            announcements = await client.get_announcements(date, date)
            
        self._save_to_file(announcements, "announcements", date)
        return announcements
    
    async def fetch_daily_contracts(self, date: datetime = None):
        """Fetch contracts for a specific day"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        async with ContrapAPIClient(self.api_config) as client:
            contracts = await client.get_contracts(date, date)
            
        self._save_to_file(contracts, "contracts", date)
        return contracts
    
    async def fetch_historical_data(
        self, 
        start_date: datetime, 
        end_date: datetime,
        data_type: str = "both"
    ):
        """Fetch historical data in daily batches"""
        current_date = start_date
        
        while current_date <= end_date:
            logger.info(f"Fetching data for {current_date.strftime('%Y-%m-%d')}")
            
            if data_type in ["announcements", "both"]:
                await self.fetch_daily_announcements(current_date)
                
            if data_type in ["contracts", "both"]:
                await self.fetch_daily_contracts(current_date)
            
            current_date += timedelta(days=1)
            
            # Small delay between days to be respectful
            await asyncio.sleep(1)
```

### Week 3: Data Processing Pipeline

#### 3.1 Create Data Validator
Create `etl/src/validator.py`:
```python
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Validate and clean data from the API"""
    
    @staticmethod
    def validate_nif(nif: str) -> bool:
        """Validate Portuguese NIF format"""
        if not nif or nif == "NULL":
            return False
            
        # Remove any non-digit characters
        nif_clean = re.sub(r'\D', '', str(nif))
        
        # Portuguese NIF should be 9 digits
        if len(nif_clean) != 9:
            return False
            
        # Basic checksum validation (simplified)
        return nif_clean[0] in ['1', '2', '5', '6', '8', '9']
    
    @staticmethod
    def normalize_date(date_str: str) -> Optional[datetime]:
        """Convert DD/MM/YYYY to datetime object"""
        if not date_str or date_str == "NULL":
            return None
            
        try:
            # Try DD/MM/YYYY format first
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            try:
                # Try YYYY-MM-DD format
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None
    
    @staticmethod
    def clean_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """Replace 'NULL' strings with None"""
        cleaned = {}
        for key, value in data.items():
            if value == "NULL" or value == "null":
                cleaned[key] = None
            elif isinstance(value, str) and value.strip() == "":
                cleaned[key] = None
            elif isinstance(value, list):
                cleaned[key] = [v for v in value if v != "NULL"]
            else:
                cleaned[key] = value
        return cleaned
    
    @staticmethod
    def extract_cpv_codes(cpv_list: List[str]) -> List[Dict[str, str]]:
        """Extract CPV codes and descriptions"""
        cpv_data = []
        for cpv_str in cpv_list:
            if not cpv_str or cpv_str == "NULL":
                continue
                
            # Format: "12345678-9 - Description"
            match = re.match(r'(\d{8}-\d)\s*-\s*(.+)', cpv_str)
            if match:
                cpv_data.append({
                    'code': match.group(1),
                    'description': match.group(2).strip()
                })
        return cpv_data
    
    @staticmethod
    def parse_competitors(competitors_list: List[str]) -> List[Dict[str, str]]:
        """Parse competitor NIFs and names"""
        parsed = []
        for competitor_str in competitors_list:
            if not competitor_str or competitor_str == "NULL":
                continue
                
            # Format: "123456789-Company Name"
            parts = competitor_str.split('-', 1)
            if len(parts) == 2:
                nif = parts[0].strip()
                name = parts[1].strip()
                if DataValidator.validate_nif(nif):
                    parsed.append({
                        'nif': nif,
                        'name': name
                    })
        return parsed
```

#### 3.2 Create Data Processor
Create `etl/src/processor.py`:
```python
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import logging
from datetime import datetime

from validator import DataValidator

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and normalize raw data for database insertion"""
    
    def __init__(self, input_dir: Path = Path("data/raw"), 
                 output_dir: Path = Path("data/processed")):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.validator = DataValidator()
        
    def process_announcements(self, filename: str) -> Dict[str, Any]:
        """Process announcements JSON file"""
        filepath = self.input_dir / filename
        
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        processed_data = {
            'announcements': [],
            'entities': set(),
            'cpv_codes': {},
            'contract_types': set()
        }
        
        for item in raw_data:
            # Clean null values
            item = self.validator.clean_null_values(item)
            
            # Process announcement
            announcement = {
                'n_anuncio': item.get('nAnuncio'),
                'id_incm': item.get('IdIncm'),
                'data_publicacao': self.validator.normalize_date(
                    item.get('dataPublicacao')
                ),
                'nif_entidade': item.get('nifEntidade'),
                'designacao_entidade': item.get('designacaoEntidade'),
                'descricao_anuncio': item.get('descricaoAnuncio'),
                'url': item.get('url'),
                'num_dr': item.get('numDR'),
                'serie': item.get('serie'),
                'tipo_acto': item.get('tipoActo'),
                'preco_base': self._parse_decimal(item.get('PrecoBase')),
                'modelo_anuncio': item.get('modeloAnuncio'),
                'ano': item.get('Ano'),
                'criter_ambient': item.get('CriterAmbient') == 'Sim',
                'prazo_propostas': item.get('PrazoPropostas'),
                'pecas_procedimento': item.get('PecasProcedimento')
            }
            
            # Validate and add entity
            if self.validator.validate_nif(announcement['nif_entidade']):
                processed_data['entities'].add(announcement['nif_entidade'])
            
            # Process CPV codes
            cpv_codes = self.validator.extract_cpv_codes(
                item.get('CPVs', [])
            )
            for cpv in cpv_codes:
                processed_data['cpv_codes'][cpv['code']] = cpv['description']
                
            announcement['cpv_codes'] = [cpv['code'] for cpv in cpv_codes]
            
            # Process contract types
            contract_types = item.get('tiposContrato', [])
            for ct in contract_types:
                if ct and ct != "NULL":
                    processed_data['contract_types'].add(ct)
            
            announcement['contract_types'] = contract_types
            
            processed_data['announcements'].append(announcement)
        
        # Convert sets to lists for JSON serialization
        processed_data['entities'] = list(processed_data['entities'])
        processed_data['contract_types'] = list(processed_data['contract_types'])
        
        # Save processed data
        output_file = self.output_dir / f"processed_{filename}"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Processed {len(processed_data['announcements'])} announcements")
        return processed_data
    
    def process_contracts(self, filename: str) -> Dict[str, Any]:
        """Process contracts JSON file"""
        filepath = self.input_dir / filename
        
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        processed_data = {
            'contracts': [],
            'entities': set(),
            'cpv_codes': {},
            'contract_types': set(),
            'competitors': {}
        }
        
        for item in raw_data:
            # Clean null values
            item = self.validator.clean_null_values(item)
            
            # Process contract
            contract = {
                'id_contrato': item.get('idcontrato'),
                'n_anuncio': item.get('nAnuncio'),
                'tipo_anuncio': item.get('TipoAnuncio'),
                'id_incm': item.get('idINCM'),
                'id_procedimento': item.get('idprocedimento'),
                'tipo_procedimento': item.get('tipoprocedimento'),
                'objecto_contrato': item.get('objectoContrato'),
                'desc_contrato': item.get('descContrato'),
                'data_publicacao': self.validator.normalize_date(
                    item.get('dataPublicacao')
                ),
                'data_celebracao': self.validator.normalize_date(
                    item.get('dataCelebracaoContrato')
                ),
                'preco_contratual': self._parse_decimal(
                    item.get('precoContratual')
                ),
                'prazo_execucao': item.get('prazoExecucao'),
                'local_execucao': item.get('localExecucao', []),
                'fundamentacao': item.get('fundamentacao'),
                'procedimento_centralizado': item.get('ProcedimentoCentralizado') == 'Sim',
                'preco_base_procedimento': self._parse_decimal(
                    item.get('precoBaseProcedimento')
                ),
                'data_decisao_adjudicacao': self.validator.normalize_date(
                    item.get('dataDecisaoAdjudicacao')
                ),
                'data_fecho_contrato': self.validator.normalize_date(
                    item.get('dataFechoContrato')
                ),
                'preco_total_efetivo': self._parse_decimal(
                    item.get('PrecoTotalEfetivo')
                ),
                'regime': item.get('regime'),
                'crit_materiais': item.get('CritMateriais') == 'Sim',
                'contrat_ecologico': item.get('ContratEcologico') == 'Sim',
                'ano': item.get('Ano'),
                'observacoes': item.get('Observacoes'),
                'link_pecas_proc': item.get('linkPecasProc')
            }
            
            # Process adjudicante (contracting entities)
            for adj_str in item.get('adjudicante', []):
                nif, name = self._parse_entity_string(adj_str)
                if self.validator.validate_nif(nif):
                    processed_data['entities'].add(nif)
                    contract['adjudicante_nif'] = nif
            
            # Process adjudicatarios (winners)
            winners = []
            for adj_str in item.get('adjudicatarios', []):
                nif, name = self._parse_entity_string(adj_str)
                if self.validator.validate_nif(nif):
                    processed_data['entities'].add(nif)
                    winners.append(nif)
            contract['adjudicatarios_nifs'] = winners
            
            # Process competitors
            competitors = self.validator.parse_competitors(
                item.get('concorrentes', [])
            )
            for competitor in competitors:
                processed_data['competitors'][competitor['nif']] = competitor['name']
                processed_data['entities'].add(competitor['nif'])
            
            contract['competitor_nifs'] = [c['nif'] for c in competitors]
            
            # Process CPV codes
            cpv_codes = self.validator.extract_cpv_codes(
                item.get('cpv', [])
            )
            for cpv in cpv_codes:
                processed_data['cpv_codes'][cpv['code']] = cpv['description']
            
            contract['cpv_codes'] = [cpv['code'] for cpv in cpv_codes]
            
            # Process contract types
            contract_types = item.get('tipoContrato', [])
            for ct in contract_types:
                if ct and ct != "NULL":
                    processed_data['contract_types'].add(ct)
            
            contract['contract_types'] = contract_types
            
            processed_data['contracts'].append(contract)
        
        # Convert sets to lists and dicts for JSON serialization
        processed_data['entities'] = list(processed_data['entities'])
        processed_data['contract_types'] = list(processed_data['contract_types'])
        
        # Save processed data
        output_file = self.output_dir / f"processed_{filename}"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Processed {len(processed_data['contracts'])} contracts")
        return processed_data
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal values from various formats"""
        if value is None or value == "NULL":
            return None
        
        try:
            # Remove currency symbols and spaces
            clean_value = str(value).replace('€', '').replace(' ', '')
            # Replace comma with dot for decimal separator
            clean_value = clean_value.replace(',', '.')
            return float(clean_value)
        except (ValueError, AttributeError):
            return None
    
    def _parse_entity_string(self, entity_str: str) -> tuple:
        """Parse entity string format: 'NIF - Name'"""
        if not entity_str or entity_str == "NULL":
            return None, None
        
        parts = entity_str.split(' - ', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return None, None
```

### Week 4: Database Loader

#### 4.1 Create Database Schema
Create `database/schema.sql`:
```sql
-- Create database schema for Contrap

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Entities table (government entities and companies)
CREATE TABLE entities (
    nif VARCHAR(9) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    num_contracts INTEGER DEFAULT 0,
    tot_adjudicatario INTEGER DEFAULT 0,
    tot_valor_contrat_ini DECIMAL(15,2),
    tot_adjudicante INTEGER DEFAULT 0,
    tot_adjudicante_valor_contrat_ini DECIMAL(15,2),
    country VARCHAR(100) DEFAULT 'Portugal',
    country_code VARCHAR(2) DEFAULT 'PT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CPV Codes lookup table
CREATE TABLE cpv_codes (
    code VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contract Types lookup table
CREATE TABLE contract_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Announcements table
CREATE TABLE announcements (
    n_anuncio VARCHAR(100) PRIMARY KEY,
    id_incm VARCHAR(50),
    data_publicacao DATE,
    nif_entidade VARCHAR(9) REFERENCES entities(nif),
    designacao_entidade VARCHAR(500),
    descricao_anuncio TEXT,
    url TEXT,
    num_dr VARCHAR(20),
    serie VARCHAR(10),
    tipo_acto VARCHAR(100),
    preco_base DECIMAL(15,2),
    modelo_anuncio VARCHAR(100),
    ano INTEGER,
    criter_ambient BOOLEAN DEFAULT FALSE,
    prazo_propostas INTEGER,
    pecas_procedimento TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contracts table
CREATE TABLE contracts (
    id_contrato VARCHAR(50) PRIMARY KEY,
    n_anuncio VARCHAR(100) REFERENCES announcements(n_anuncio),
    tipo_anuncio VARCHAR(100),
    id_incm VARCHAR(50),
    id_procedimento VARCHAR(50),
    tipo_procedimento VARCHAR(100),
    objecto_contrato TEXT,
    desc_contrato TEXT,
    adjudicante_nif VARCHAR(9) REFERENCES entities(nif),
    data_publicacao DATE,
    data_celebracao DATE,
    preco_contratual DECIMAL(15,2),
    prazo_execucao INTEGER,
    local_execucao TEXT[],
    fundamentacao TEXT,
    procedimento_centralizado BOOLEAN DEFAULT FALSE,
    num_acordo_quadro VARCHAR(100),
    descr_acordo_quadro TEXT,
    preco_base_procedimento DECIMAL(15,2),
    data_decisao_adjudicacao DATE,
    data_fecho_contrato DATE,
    preco_total_efetivo DECIMAL(15,2),
    regime TEXT,
    justif_n_reduc_escr_contrato TEXT,
    tipo_fim_contrato VARCHAR(100),
    crit_materiais BOOLEAN DEFAULT FALSE,
    link_pecas_proc TEXT,
    observacoes TEXT,
    contrat_ecologico BOOLEAN DEFAULT FALSE,
    ano INTEGER,
    fundament_ajuste_direto TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Association Tables (Many-to-Many relationships)

-- Announcement Contract Types
CREATE TABLE announcement_contract_types (
    announcement_id VARCHAR(100) REFERENCES announcements(n_anuncio),
    contract_type_id INTEGER REFERENCES contract_types(id),
    PRIMARY KEY (announcement_id, contract_type_id)
);

-- Announcement CPV Codes
CREATE TABLE announcement_cpv_codes (
    announcement_id VARCHAR(100) REFERENCES announcements(n_anuncio),
    cpv_code VARCHAR(20) REFERENCES cpv_codes(code),
    PRIMARY KEY (announcement_id, cpv_code)
);

-- Contract Contract Types
CREATE TABLE contract_contract_types (
    contract_id VARCHAR(50) REFERENCES contracts(id_contrato),
    contract_type_id INTEGER REFERENCES contract_types(id),
    PRIMARY KEY (contract_id, contract_type_id)
);

-- Contract CPV Codes
CREATE TABLE contract_cpv_codes (
    contract_id VARCHAR(50) REFERENCES contracts(id_contrato),
    cpv_code VARCHAR(20) REFERENCES cpv_codes(code),
    PRIMARY KEY (contract_id, cpv_code)
);

-- Contract Competitors
CREATE TABLE contract_competitors (
    contract_id VARCHAR(50) REFERENCES contracts(id_contrato),
    competitor_nif VARCHAR(9) REFERENCES entities(nif),
    PRIMARY KEY (contract_id, competitor_nif)
);

-- Contract Winners (Adjudicatarios)
CREATE TABLE contract_winners (
    contract_id VARCHAR(50) REFERENCES contracts(id_contrato),
    winner_nif VARCHAR(9) REFERENCES entities(nif),
    PRIMARY KEY (contract_id, winner_nif)
);

-- Indexes for performance
CREATE INDEX idx_announcements_date ON announcements(data_publicacao);
CREATE INDEX idx_announcements_entity ON announcements(nif_entidade);
CREATE INDEX idx_announcements_year ON announcements(ano);

CREATE INDEX idx_contracts_date ON contracts(data_publicacao);
CREATE INDEX idx_contracts_adjudicante ON contracts(adjudicante_nif);
CREATE INDEX idx_contracts_year ON contracts(ano);
CREATE INDEX idx_contracts_price ON contracts(preco_contratual);

-- Full-text search indexes
CREATE INDEX idx_announcements_description ON announcements USING gin(to_tsvector('portuguese', descricao_anuncio));
CREATE INDEX idx_contracts_object ON contracts USING gin(to_tsvector('portuguese', objecto_contrato));

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_announcements_updated_at BEFORE UPDATE ON announcements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at BEFORE UPDATE ON contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

#### 4.2 Create Database Loader
Create `etl/src/loader.py`:
```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import json
from pathlib import Path
from typing import Dict, Any, List
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class DatabaseLoader:
    """Load processed data into PostgreSQL database"""
    
    def __init__(self):
        self.db_url = os.getenv(
            'DATABASE_URL', 
            'postgresql://contrap_user:password@localhost:5432/contrap'
        )
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        
    def load_processed_file(self, filepath: Path):
        """Load a processed JSON file into the database"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        session = self.Session()
        try:
            # Load in order: lookup tables first, then main tables, then associations
            
            # 1. Load entities (if present)
            if 'entities' in data:
                self._load_entities(session, data['entities'])
            
            # 2. Load CPV codes
            if 'cpv_codes' in data:
                self._load_cpv_codes(session, data['cpv_codes'])
            
            # 3. Load contract types
            if 'contract_types' in data:
                self._load_contract_types(session, data['contract_types'])
            
            # 4. Load announcements
            if 'announcements' in data:
                self._load_announcements(session, data['announcements'])
            
            # 5. Load contracts
            if 'contracts' in data:
                self._load_contracts(session, data['contracts'])
            
            session.commit()
            logger.info(f"Successfully loaded data from {filepath}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error loading data: {str(e)}")
            raise
        finally:
            session.close()
    
    def _load_entities(self, session, entity_nifs: List[str]):
        """Load or update entities"""
        for nif in entity_nifs:
            if not nif:
                continue
                
            # Check if entity exists
            result = session.execute(
                text("SELECT nif FROM entities WHERE nif = :nif"),
                {"nif": nif}
            ).first()
            
            if not result:
                # Insert new entity with placeholder name
                session.execute(
                    text("""
                        INSERT INTO entities (nif, name) 
                        VALUES (:nif, :name)
                        ON CONFLICT (nif) DO NOTHING
                    """),
                    {"nif": nif, "name": f"Entity {nif}"}
                )
        
        session.flush()
    
    def _load_cpv_codes(self, session, cpv_codes: Dict[str, str]):
        """Load CPV codes"""
        for code, description in cpv_codes.items():
            session.execute(
                text("""
                    INSERT INTO cpv_codes (code, description)
                    VALUES (:code, :description)
                    ON CONFLICT (code) DO UPDATE
                    SET description = EXCLUDED.description
                """),
                {"code": code, "description": description}
            )
        
        session.flush()
    
    def _load_contract_types(self, session, contract_types: List[str]):
        """Load contract types"""
        for ct_name in contract_types:
            if not ct_name:
                continue
                
            session.execute(
                text("""
                    INSERT INTO contract_types (name)
                    VALUES (:name)
                    ON CONFLICT (name) DO NOTHING
                """),
                {"name": ct_name}
            )
        
        session.flush()
    
    def _load_announcements(self, session, announcements: List[Dict[str, Any]]):
        """Load announcements and their associations"""
        for announcement in announcements:
            # Insert main announcement record
            session.execute(
                text("""
                    INSERT INTO announcements (
                        n_anuncio, id_incm, data_publicacao, nif_entidade,
                        designacao_entidade, descricao_anuncio, url, num_dr,
                        serie, tipo_acto, preco_base, modelo_anuncio, ano,
                        criter_ambient, prazo_propostas, pecas_procedimento
                    ) VALUES (
                        :n_anuncio, :id_incm, :data_publicacao, :nif_entidade,
                        :designacao_entidade, :descricao_anuncio, :url, :num_dr,
                        :serie, :tipo_acto, :preco_base, :modelo_anuncio, :ano,
                        :criter_ambient, :prazo_propostas, :pecas_procedimento
                    )
                    ON CONFLICT (n_anuncio) DO UPDATE SET
                        data_publicacao = EXCLUDED.data_publicacao,
                        preco_base = EXCLUDED.preco_base,
                        updated_at = CURRENT_TIMESTAMP
                """),
                announcement
            )
            
            # Load CPV associations
            for cpv_code in announcement.get('cpv_codes', []):
                session.execute(
                    text("""
                        INSERT INTO announcement_cpv_codes (announcement_id, cpv_code)
                        VALUES (:announcement_id, :cpv_code)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "announcement_id": announcement['n_anuncio'],
                        "cpv_code": cpv_code
                    }
                )
            
            # Load contract type associations
            for ct_name in announcement.get('contract_types', []):
                # Get contract type ID
                ct_id = session.execute(
                    text("SELECT id FROM contract_types WHERE name = :name"),
                    {"name": ct_name}
                ).scalar()
                
                if ct_id:
                    session.execute(
                        text("""
                            INSERT INTO announcement_contract_types 
                            (announcement_id, contract_type_id)
                            VALUES (:announcement_id, :contract_type_id)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "announcement_id": announcement['n_anuncio'],
                            "contract_type_id": ct_id
                        }
                    )
        
        session.flush()
    
    def _load_contracts(self, session, contracts: List[Dict[str, Any]]):
        """Load contracts and their associations"""
        for contract in contracts:
            # Insert main contract record
            session.execute(
                text("""
                    INSERT INTO contracts (
                        id_contrato, n_anuncio, tipo_anuncio, id_incm,
                        id_procedimento, tipo_procedimento, objecto_contrato,
                        desc_contrato, adjudicante_nif, data_publicacao,
                        data_celebracao, preco_contratual, prazo_execucao,
                        local_execucao, fundamentacao, procedimento_centralizado,
                        preco_base_procedimento, data_decisao_adjudicacao,
                        data_fecho_contrato, preco_total_efetivo, regime,
                        crit_materiais, link_pecas_proc, observacoes,
                        contrat_ecologico, ano
                    ) VALUES (
                        :id_contrato, :n_anuncio, :tipo_anuncio, :id_incm,
                        :id_procedimento, :tipo_procedimento, :objecto_contrato,
                        :desc_contrato, :adjudicante_nif, :data_publicacao,
                        :data_celebracao, :preco_contratual, :prazo_execucao,
                        :local_execucao, :fundamentacao, :procedimento_centralizado,
                        :preco_base_procedimento, :data_decisao_adjudicacao,
                        :data_fecho_contrato, :preco_total_efetivo, :regime,
                        :crit_materiais, :link_pecas_proc, :observacoes,
                        :contrat_ecologico, :ano
                    )
                    ON CONFLICT (id_contrato) DO UPDATE SET
                        preco_contratual = EXCLUDED.preco_contratual,
                        preco_total_efetivo = EXCLUDED.preco_total_efetivo,
                        data_fecho_contrato = EXCLUDED.data_fecho_contrato,
                        updated_at = CURRENT_TIMESTAMP
                """),
                contract
            )
            
            # Load winner associations
            for winner_nif in contract.get('adjudicatarios_nifs', []):
                session.execute(
                    text("""
                        INSERT INTO contract_winners (contract_id, winner_nif)
                        VALUES (:contract_id, :winner_nif)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "contract_id": contract['id_contrato'],
                        "winner_nif": winner_nif
                    }
                )
            
            # Load competitor associations
            for competitor_nif in contract.get('competitor_nifs', []):
                session.execute(
                    text("""
                        INSERT INTO contract_competitors (contract_id, competitor_nif)
                        VALUES (:contract_id, :competitor_nif)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "contract_id": contract['id_contrato'],
                        "competitor_nif": competitor_nif
                    }
                )
            
            # Load CPV associations
            for cpv_code in contract.get('cpv_codes', []):
                session.execute(
                    text("""
                        INSERT INTO contract_cpv_codes (contract_id, cpv_code)
                        VALUES (:contract_id, :cpv_code)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "contract_id": contract['id_contrato'],
                        "cpv_code": cpv_code
                    }
                )
            
            # Load contract type associations
            for ct_name in contract.get('contract_types', []):
                # Get contract type ID
                ct_id = session.execute(
                    text("SELECT id FROM contract_types WHERE name = :name"),
                    {"name": ct_name}
                ).scalar()
                
                if ct_id:
                    session.execute(
                        text("""
                            INSERT INTO contract_contract_types 
                            (contract_id, contract_type_id)
                            VALUES (:contract_id, :contract_type_id)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "contract_id": contract['id_contrato'],
                            "contract_type_id": ct_id
                        }
                    )
        
        session.flush()
```

---

## Phase 2: Database & Data Processing (Weeks 5-6)

### Week 5: ETL Orchestration

#### 5.1 Create Main ETL Pipeline
Create `etl/src/pipeline.py`:
```python
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import time
import os

from fetcher import DataFetcher
from processor import DataProcessor
from loader import DatabaseLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ETLPipeline:
    """Main ETL pipeline orchestrator"""
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.processor = DataProcessor()
        self.loader = DatabaseLoader()
        
    async def run_daily_pipeline(self):
        """Run the daily ETL pipeline"""
        logger.info("Starting daily ETL pipeline")
        
        try:
            # Yesterday's data
            yesterday = datetime.now() - timedelta(days=1)
            
            # Fetch data
            logger.info("Fetching announcements...")
            await self.fetcher.fetch_daily_announcements(yesterday)
            
            logger.info("Fetching contracts...")
            await self.fetcher.fetch_daily_contracts(yesterday)
            
            # Process data
            logger.info("Processing data...")
            self._process_recent_files()
            
            # Load to database
            logger.info("Loading to database...")
            self._load_processed_files()
            
            logger.info("Daily ETL pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {str(e)}")
            raise
    
    def _process_recent_files(self):
        """Process recent raw data files"""
        raw_dir = Path("data/raw")
        processed_dir = Path("data/processed")
        
        # Get files from the last 2 days
        cutoff_date = datetime.now() - timedelta(days=2)
        
        for file in raw_dir.glob("*.json"):
            # Check if already processed
            processed_file = processed_dir / f"processed_{file.name}"
            if processed_file.exists():
                continue
            
            # Check file date
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if file_mtime < cutoff_date:
                continue
            
            # Process based on file type
            if "announcements" in file.name:
                self.processor.process_announcements(file.name)
            elif "contracts" in file.name:
                self.processor.process_contracts(file.name)
    
    def _load_processed_files(self):
        """Load processed files to database"""
        processed_dir = Path("data/processed")
        
        # Track loaded files
        loaded_tracker = processed_dir / ".loaded"
        loaded_files = set()
        
        if loaded_tracker.exists():
            with open(loaded_tracker, 'r') as f:
                loaded_files = set(line.strip() for line in f)
        
        # Load new files
        for file in processed_dir.glob("processed_*.json"):
            if file.name in loaded_files:
                continue
            
            try:
                self.loader.load_processed_file(file)
                loaded_files.add(file.name)
                
                # Update tracker
                with open(loaded_tracker, 'a') as f:
                    f.write(f"{file.name}\n")
                    
            except Exception as e:
                logger.error(f"Failed to load {file.name}: {str(e)}")
    
    async def run_historical_backfill(self, start_date: datetime, end_date: datetime):
        """Run historical data backfill"""
        logger.info(f"Starting historical backfill from {start_date} to {end_date}")
        
        # Fetch historical data
        await self.fetcher.fetch_historical_data(start_date, end_date)
        
        # Process all files
        raw_dir = Path("data/raw")
        for file in raw_dir.glob("*.json"):
            if "announcements" in file.name:
                self.processor.process_announcements(file.name)
            elif "contracts" in file.name:
                self.processor.process_contracts(file.name)
        
        # Load all processed files
        self._load_processed_files()
        
        logger.info("Historical backfill completed")

def main():
    """Main entry point for ETL pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Contrap ETL Pipeline')
    parser.add_argument('--mode', choices=['daily', 'backfill', 'scheduler'], 
                       default='daily', help='Pipeline mode')
    parser.add_argument('--start-date', help='Start date for backfill (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for backfill (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    pipeline = ETLPipeline()
    
    if args.mode == 'daily':
        # Run once
        asyncio.run(pipeline.run_daily_pipeline())
        
    elif args.mode == 'backfill':
        # Run historical backfill
        if not args.start_date or not args.end_date:
            print("Start date and end date required for backfill")
            return
        
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        asyncio.run(pipeline.run_historical_backfill(start_date, end_date))
        
    elif args.mode == 'scheduler':
        # Run on schedule
        schedule.every(6).hours.do(
            lambda: asyncio.run(pipeline.run_daily_pipeline())
        )
        
        logger.info("ETL scheduler started. Running every 6 hours...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
```

### Week 6: Testing & Monitoring

#### 6.0 Data Quality Insights & Normalization Rules

##### Key Data Quality Challenges Discovered

**1. Competitor Data Issues**
- **19,914 unique competitor entities** found in the data
- Pattern: "500035121-Caetano Formula, S.A." (NIF-Name format)
- **Invalid NIFs found**: "000000000", "ESA28125078", "0.760.604.615"
- **International entities**: Non-Portuguese entities (ESA*, FI* prefixes)
- **Duplicates**: "_duplicado" suffix indicates duplicate entries

**2. NIF Validation Rules**
```python
# Portuguese NIF must be exactly 9 digits
# First digit must be 1, 2, 5, 6, 8, or 9 (valid entity types)
PORTUGUESE_NIF_PATTERN = r'^[125689][0-9]{8}$'

# Invalid patterns to reject:
INVALID_PATTERNS = [
    '000000000',  # All zeros
    '999999999',  # Test data
    '123456789',  # Sequential
]
```

**3. Data Cleaning Requirements**
- Remove entries with "_duplicado" suffix
- Validate NIF format before entity creation
- Handle international entities separately
- Clean "NULL" strings and convert to None
- Normalize company names (remove extra spaces, standardize case)

**4. Contract Type Normalization**
Standardize to these categories:
- **Services**: "Aquisição de serviços"
- **Goods**: "Aquisição de bens móveis"
- **Works**: "Empreitadas de obras públicas"
- **Rental**: "Locação de bens móveis"

**5. CPV Code Hierarchy**
- Extract 8-digit code from format: "63510000-7 - Description"
- Build hierarchy: First 2 digits = Division, First 3 = Group, etc.
- Validate against EU CPV standard codes

#### 6.1 Create ETL Tests
Create `etl/tests/test_validator.py`:
```python
import pytest
from datetime import datetime
from src.validator import DataValidator

class TestDataValidator:
    
    def test_validate_nif_valid(self):
        assert DataValidator.validate_nif("123456789") == True
        assert DataValidator.validate_nif("501234567") == True
    
    def test_validate_nif_invalid(self):
        assert DataValidator.validate_nif("12345678") == False  # Too short
        assert DataValidator.validate_nif("1234567890") == False  # Too long
        assert DataValidator.validate_nif("NULL") == False
        assert DataValidator.validate_nif("") == False
        assert DataValidator.validate_nif(None) == False
    
    def test_normalize_date(self):
        # DD/MM/YYYY format
        result = DataValidator.normalize_date("25/12/2024")
        assert result == datetime(2024, 12, 25)
        
        # YYYY-MM-DD format
        result = DataValidator.normalize_date("2024-12-25")
        assert result == datetime(2024, 12, 25)
        
        # Invalid formats
        assert DataValidator.normalize_date("NULL") is None
        assert DataValidator.normalize_date("") is None
        assert DataValidator.normalize_date("invalid") is None
    
    def test_clean_null_values(self):
        data = {
            "field1": "value",
            "field2": "NULL",
            "field3": "",
            "field4": ["item1", "NULL", "item2"],
            "field5": None
        }
        
        cleaned = DataValidator.clean_null_values(data)
        
        assert cleaned["field1"] == "value"
        assert cleaned["field2"] is None
        assert cleaned["field3"] is None
        assert cleaned["field4"] == ["item1", "item2"]
        assert cleaned["field5"] is None
    
    def test_extract_cpv_codes(self):
        cpv_list = [
            "12345678-9 - Test Description",
            "98765432-1 - Another Description",
            "NULL",
            ""
        ]
        
        result = DataValidator.extract_cpv_codes(cpv_list)
        
        assert len(result) == 2
        assert result[0]["code"] == "12345678-9"
        assert result[0]["description"] == "Test Description"
        assert result[1]["code"] == "98765432-1"
    
    def test_parse_competitors(self):
        competitors = [
            "123456789-Company A",
            "987654321-Company B",
            "invalid-Company C",
            "NULL"
        ]
        
        result = DataValidator.parse_competitors(competitors)
        
        assert len(result) == 2
        assert result[0]["nif"] == "123456789"
        assert result[0]["name"] == "Company A"
```

#### 6.2 Create Monitoring Script
Create `etl/src/monitor.py`:
```python
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os

logger = logging.getLogger(__name__)

class ETLMonitor:
    """Monitor ETL pipeline health and data quality"""
    
    def __init__(self):
        self.db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://contrap_user:password@localhost:5432/contrap'
        )
        self.engine = create_engine(self.db_url)
    
    def check_data_freshness(self) -> dict:
        """Check how recent the data is"""
        with self.engine.connect() as conn:
            # Check latest announcement
            latest_announcement = conn.execute(
                text("""
                    SELECT MAX(data_publicacao) as latest_date,
                           COUNT(*) as total_count
                    FROM announcements
                """)
            ).first()
            
            # Check latest contract
            latest_contract = conn.execute(
                text("""
                    SELECT MAX(data_publicacao) as latest_date,
                           COUNT(*) as total_count
                    FROM contracts
                """)
            ).first()
            
            # Check today's data
            today = datetime.now().date()
            today_announcements = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM announcements
                    WHERE data_publicacao = :today
                """),
                {"today": today}
            ).scalar()
            
            today_contracts = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM contracts
                    WHERE data_publicacao = :today
                """),
                {"today": today}
            ).scalar()
        
        return {
            "announcements": {
                "latest_date": latest_announcement.latest_date,
                "total_count": latest_announcement.total_count,
                "today_count": today_announcements
            },
            "contracts": {
                "latest_date": latest_contract.latest_date,
                "total_count": latest_contract.total_count,
                "today_count": today_contracts
            }
        }
    
    def check_data_quality(self) -> dict:
        """Check data quality metrics"""
        with self.engine.connect() as conn:
            # Check for missing required fields
            missing_nif = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM announcements
                    WHERE nif_entidade IS NULL
                """)
            ).scalar()
            
            # Check for invalid dates
            future_dates = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM announcements
                    WHERE data_publicacao > CURRENT_DATE
                """)
            ).scalar()
            
            # Check for orphaned contracts
            orphaned_contracts = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM contracts c
                    LEFT JOIN announcements a ON c.n_anuncio = a.n_anuncio
                    WHERE a.n_anuncio IS NULL AND c.n_anuncio IS NOT NULL
                """)
            ).scalar()
            
            # Check for duplicate entries
            duplicate_announcements = conn.execute(
                text("""
                    SELECT COUNT(*) - COUNT(DISTINCT n_anuncio) as duplicates
                    FROM announcements
                """)
            ).scalar()
        
        return {
            "missing_nif": missing_nif,
            "future_dates": future_dates,
            "orphaned_contracts": orphaned_contracts,
            "duplicate_announcements": duplicate_announcements
        }
    
    def generate_report(self) -> str:
        """Generate a health report"""
        freshness = self.check_data_freshness()
        quality = self.check_data_quality()
        
        report = f"""
ETL Pipeline Health Report
Generated: {datetime.now().isoformat()}

DATA FRESHNESS:
--------------
Announcements:
  Latest Date: {freshness['announcements']['latest_date']}
  Total Count: {freshness['announcements']['total_count']}
  Today's Count: {freshness['announcements']['today_count']}

Contracts:
  Latest Date: {freshness['contracts']['latest_date']}
  Total Count: {freshness['contracts']['total_count']}
  Today's Count: {freshness['contracts']['today_count']}

DATA QUALITY:
------------
Issues Found:
  Missing NIFs: {quality['missing_nif']}
  Future Dates: {quality['future_dates']}
  Orphaned Contracts: {quality['orphaned_contracts']}
  Duplicate Announcements: {quality['duplicate_announcements']}
"""
        return report

if __name__ == "__main__":
    monitor = ETLMonitor()
    print(monitor.generate_report())
```

---

## Phase 3: Backend API Development (Weeks 7-9)

### Week 7: GraphQL API Setup

#### 7.1 Initialize Node.js Backend
```bash
cd backend
npm init -y
npm install apollo-server-express express graphql prisma @prisma/client
npm install --save-dev @types/node typescript ts-node nodemon
```

Create `backend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

#### 7.2 Setup Prisma ORM
Create `backend/prisma/schema.prisma`:
```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Entity {
  nif                       String         @id
  name                      String
  numContracts             Int            @default(0)
  totAdjudicatario         Int            @default(0)
  totValorContratIni       Decimal?       @db.Decimal(15, 2)
  totAdjudicante           Int            @default(0)
  totAdjudicanteValorIni   Decimal?       @db.Decimal(15, 2)
  country                  String         @default("Portugal")
  countryCode              String         @default("PT")
  createdAt                DateTime       @default(now())
  updatedAt                DateTime       @updatedAt
  
  announcements            Announcement[]  @relation("EntityAnnouncements")
  contractsAsAdjudicante   Contract[]      @relation("AdjudicanteContracts")
  contractsAsWinner        ContractWinner[]
  contractsAsCompetitor    ContractCompetitor[]
  
  @@map("entities")
}

model CpvCode {
  code         String   @id
  description  String
  createdAt    DateTime @default(now())
  
  announcements AnnouncementCpv[]
  contracts     ContractCpv[]
  
  @@map("cpv_codes")
}

model ContractType {
  id        Int      @id @default(autoincrement())
  name      String   @unique
  createdAt DateTime @default(now())
  
  announcements AnnouncementContractType[]
  contracts     ContractContractType[]
  
  @@map("contract_types")
}

model Announcement {
  nAnuncio            String   @id
  idIncm              String?
  dataPublicacao      DateTime?
  nifEntidade         String?
  entity              Entity?   @relation("EntityAnnouncements", fields: [nifEntidade], references: [nif])
  designacaoEntidade  String?
  descricaoAnuncio    String?
  url                 String?
  numDr               String?
  serie               String?
  tipoActo            String?
  precoBase           Decimal?  @db.Decimal(15, 2)
  modeloAnuncio       String?
  ano                 Int?
  criterAmbient       Boolean   @default(false)
  prazoPropostas      Int?
  pecasProcedimento   String?
  createdAt           DateTime  @default(now())
  updatedAt           DateTime  @updatedAt
  
  contracts           Contract[]
  cpvCodes           AnnouncementCpv[]
  contractTypes      AnnouncementContractType[]
  
  @@index([dataPublicacao])
  @@index([nifEntidade])
  @@index([ano])
  @@map("announcements")
}

model Contract {
  idContrato               String    @id
  nAnuncio                 String?
  announcement             Announcement? @relation(fields: [nAnuncio], references: [nAnuncio])
  tipoAnuncio              String?
  idIncm                   String?
  idProcedimento           String?
  tipoProcedimento         String?
  objectoContrato          String?
  descContrato             String?
  adjudicanteNif           String?
  adjudicante              Entity?   @relation("AdjudicanteContracts", fields: [adjudicanteNif], references: [nif])
  dataPublicacao           DateTime?
  dataCelebracao           DateTime?
  precoContratual          Decimal?  @db.Decimal(15, 2)
  prazoExecucao            Int?
  localExecucao            String[]
  fundamentacao            String?
  procedimentoCentralizado Boolean   @default(false)
  numAcordoQuadro          String?
  descrAcordoQuadro        String?
  precoBaseProcedimento    Decimal?  @db.Decimal(15, 2)
  dataDecisaoAdjudicacao   DateTime?
  dataFechoContrato        DateTime?
  precoTotalEfetivo        Decimal?  @db.Decimal(15, 2)
  regime                   String?
  critMateriais            Boolean   @default(false)
  linkPecasProc            String?
  observacoes              String?
  contratEcologico         Boolean   @default(false)
  ano                      Int?
  createdAt                DateTime  @default(now())
  updatedAt                DateTime  @updatedAt
  
  winners                  ContractWinner[]
  competitors              ContractCompetitor[]
  cpvCodes                ContractCpv[]
  contractTypes           ContractContractType[]
  
  @@index([dataPublicacao])
  @@index([adjudicanteNif])
  @@index([ano])
  @@index([precoContratual])
  @@map("contracts")
}

// Association tables
model AnnouncementContractType {
  announcementId String
  contractTypeId Int
  announcement   Announcement @relation(fields: [announcementId], references: [nAnuncio])
  contractType   ContractType @relation(fields: [contractTypeId], references: [id])
  
  @@id([announcementId, contractTypeId])
  @@map("announcement_contract_types")
}

model AnnouncementCpv {
  announcementId String
  cpvCode        String
  announcement   Announcement @relation(fields: [announcementId], references: [nAnuncio])
  cpv            CpvCode     @relation(fields: [cpvCode], references: [code])
  
  @@id([announcementId, cpvCode])
  @@map("announcement_cpv_codes")
}

model ContractContractType {
  contractId     String
  contractTypeId Int
  contract       Contract     @relation(fields: [contractId], references: [idContrato])
  contractType   ContractType @relation(fields: [contractTypeId], references: [id])
  
  @@id([contractId, contractTypeId])
  @@map("contract_contract_types")
}

model ContractCpv {
  contractId String
  cpvCode    String
  contract   Contract @relation(fields: [contractId], references: [idContrato])
  cpv        CpvCode  @relation(fields: [cpvCode], references: [code])
  
  @@id([contractId, cpvCode])
  @@map("contract_cpv_codes")
}

model ContractWinner {
  contractId String
  winnerNif  String
  contract   Contract @relation(fields: [contractId], references: [idContrato])
  winner     Entity   @relation(fields: [winnerNif], references: [nif])
  
  @@id([contractId, winnerNif])
  @@map("contract_winners")
}

model ContractCompetitor {
  contractId    String
  competitorNif String
  contract      Contract @relation(fields: [contractId], references: [idContrato])
  competitor    Entity   @relation(fields: [competitorNif], references: [nif])
  
  @@id([contractId, competitorNif])
  @@map("contract_competitors")
}
```

### Week 8: GraphQL Schema & Resolvers

#### 8.1 Create GraphQL Type Definitions
Create `backend/src/schema/typeDefs.ts`:
```typescript
import { gql } from 'apollo-server-express';

export const typeDefs = gql`
  scalar DateTime
  scalar Decimal

  type Entity {
    nif: String!
    name: String!
    numContracts: Int
    totAdjudicatario: Int
    totValorContratIni: Decimal
    country: String
    announcements: [Announcement!]
    contractsAsAdjudicante: [Contract!]
    contractsAsWinner: [Contract!]
  }

  type CpvCode {
    code: String!
    description: String!
  }

  type ContractType {
    id: Int!
    name: String!
  }

  type Announcement {
    nAnuncio: String!
    dataPublicacao: DateTime
    entity: Entity
    designacaoEntidade: String
    descricaoAnuncio: String
    url: String
    precoBase: Decimal
    modeloAnuncio: String
    ano: Int
    criterAmbient: Boolean
    prazoPropostas: Int
    contracts: [Contract!]
    cpvCodes: [CpvCode!]
    contractTypes: [ContractType!]
  }

  type Contract {
    idContrato: String!
    announcement: Announcement
    objectoContrato: String
    adjudicante: Entity
    dataPublicacao: DateTime
    dataCelebracao: DateTime
    precoContratual: Decimal
    prazoExecucao: Int
    localExecucao: [String!]
    winners: [Entity!]
    competitors: [Entity!]
    cpvCodes: [CpvCode!]
    contractTypes: [ContractType!]
  }

  type AnnouncementConnection {
    edges: [AnnouncementEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }

  type AnnouncementEdge {
    node: Announcement!
    cursor: String!
  }

  type ContractConnection {
    edges: [ContractEdge!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }

  type ContractEdge {
    node: Contract!
    cursor: String!
  }

  type PageInfo {
    hasNextPage: Boolean!
    hasPreviousPage: Boolean!
    startCursor: String
    endCursor: String
  }

  type Analytics {
    totalAnnouncements: Int!
    totalContracts: Int!
    totalValue: Decimal!
    averageValue: Decimal!
    topEntities: [EntityStats!]!
    topCpvCodes: [CpvStats!]!
  }

  type EntityStats {
    entity: Entity!
    contractCount: Int!
    totalValue: Decimal!
  }

  type CpvStats {
    cpvCode: CpvCode!
    count: Int!
    totalValue: Decimal!
  }

  input AnnouncementFilter {
    startDate: DateTime
    endDate: DateTime
    nifEntidade: String
    cpvCode: String
    contractType: String
    minPrice: Decimal
    maxPrice: Decimal
    region: String
  }

  input ContractFilter {
    startDate: DateTime
    endDate: DateTime
    adjudicanteNif: String
    winnerNif: String
    cpvCode: String
    contractType: String
    minValue: Decimal
    maxValue: Decimal
  }

  input Pagination {
    first: Int
    after: String
    last: Int
    before: String
  }

  type Query {
    # Announcements
    announcements(
      filter: AnnouncementFilter
      pagination: Pagination
    ): AnnouncementConnection!
    
    announcement(nAnuncio: String!): Announcement
    
    # Contracts
    contracts(
      filter: ContractFilter
      pagination: Pagination
    ): ContractConnection!
    
    contract(idContrato: String!): Contract
    
    # Entities
    entity(nif: String!): Entity
    entities(search: String, limit: Int): [Entity!]!
    
    # Analytics
    marketAnalytics(
      startDate: DateTime!
      endDate: DateTime!
      region: String
    ): Analytics!
    
    competitorAnalysis(nif: String!): EntityStats
    
    # Lookups
    cpvCodes(search: String): [CpvCode!]!
    contractTypes: [ContractType!]!
  }

  type Mutation {
    # Admin operations (protected)
    updateEntity(nif: String!, name: String!): Entity
  }
`;
```

#### 8.2 Create Resolvers
Create `backend/src/resolvers/index.ts`:
```typescript
import { PrismaClient } from '@prisma/client';
import { DateTimeResolver } from 'graphql-scalars';

const prisma = new PrismaClient();

export const resolvers = {
  DateTime: DateTimeResolver,
  
  Query: {
    // Announcements
    announcements: async (_, { filter = {}, pagination = {} }) => {
      const where = buildAnnouncementWhere(filter);
      const take = pagination.first || 20;
      const skip = pagination.after ? 1 : 0;
      
      const announcements = await prisma.announcement.findMany({
        where,
        take,
        skip,
        cursor: pagination.after ? { nAnuncio: pagination.after } : undefined,
        orderBy: { dataPublicacao: 'desc' },
        include: {
          entity: true,
          cpvCodes: { include: { cpv: true } },
          contractTypes: { include: { contractType: true } }
        }
      });
      
      const totalCount = await prisma.announcement.count({ where });
      
      return {
        edges: announcements.map(node => ({
          node,
          cursor: node.nAnuncio
        })),
        pageInfo: {
          hasNextPage: announcements.length === take,
          hasPreviousPage: !!pagination.after,
          startCursor: announcements[0]?.nAnuncio,
          endCursor: announcements[announcements.length - 1]?.nAnuncio
        },
        totalCount
      };
    },
    
    announcement: async (_, { nAnuncio }) => {
      return prisma.announcement.findUnique({
        where: { nAnuncio },
        include: {
          entity: true,
          contracts: true,
          cpvCodes: { include: { cpv: true } },
          contractTypes: { include: { contractType: true } }
        }
      });
    },
    
    // Contracts
    contracts: async (_, { filter = {}, pagination = {} }) => {
      const where = buildContractWhere(filter);
      const take = pagination.first || 20;
      const skip = pagination.after ? 1 : 0;
      
      const contracts = await prisma.contract.findMany({
        where,
        take,
        skip,
        cursor: pagination.after ? { idContrato: pagination.after } : undefined,
        orderBy: { dataPublicacao: 'desc' },
        include: {
          announcement: true,
          adjudicante: true,
          winners: { include: { winner: true } },
          competitors: { include: { competitor: true } },
          cpvCodes: { include: { cpv: true } },
          contractTypes: { include: { contractType: true } }
        }
      });
      
      const totalCount = await prisma.contract.count({ where });
      
      return {
        edges: contracts.map(node => ({
          node,
          cursor: node.idContrato
        })),
        pageInfo: {
          hasNextPage: contracts.length === take,
          hasPreviousPage: !!pagination.after,
          startCursor: contracts[0]?.idContrato,
          endCursor: contracts[contracts.length - 1]?.idContrato
        },
        totalCount
      };
    },
    
    contract: async (_, { idContrato }) => {
      return prisma.contract.findUnique({
        where: { idContrato },
        include: {
          announcement: true,
          adjudicante: true,
          winners: { include: { winner: true } },
          competitors: { include: { competitor: true } },
          cpvCodes: { include: { cpv: true } },
          contractTypes: { include: { contractType: true } }
        }
      });
    },
    
    // Entities
    entity: async (_, { nif }) => {
      return prisma.entity.findUnique({
        where: { nif }
      });
    },
    
    entities: async (_, { search, limit = 10 }) => {
      return prisma.entity.findMany({
        where: search ? {
          OR: [
            { name: { contains: search, mode: 'insensitive' } },
            { nif: { contains: search } }
          ]
        } : undefined,
        take: limit
      });
    },
    
    // Analytics
    marketAnalytics: async (_, { startDate, endDate, region }) => {
      const [
        totalAnnouncements,
        totalContracts,
        contractStats,
        topEntities,
        topCpvCodes
      ] = await Promise.all([
        prisma.announcement.count({
          where: {
            dataPublicacao: { gte: startDate, lte: endDate }
          }
        }),
        
        prisma.contract.count({
          where: {
            dataPublicacao: { gte: startDate, lte: endDate }
          }
        }),
        
        prisma.contract.aggregate({
          where: {
            dataPublicacao: { gte: startDate, lte: endDate }
          },
          _sum: { precoContratual: true },
          _avg: { precoContratual: true }
        }),
        
        prisma.$queryRaw`
          SELECT e.nif, e.name, COUNT(c.*) as contract_count,
                 SUM(c.preco_contratual) as total_value
          FROM contracts c
          JOIN entities e ON c.adjudicante_nif = e.nif
          WHERE c.data_publicacao >= ${startDate}
            AND c.data_publicacao <= ${endDate}
          GROUP BY e.nif, e.name
          ORDER BY total_value DESC
          LIMIT 10
        `,
        
        prisma.$queryRaw`
          SELECT cp.code, cp.description, COUNT(*) as count,
                 SUM(c.preco_contratual) as total_value
          FROM contracts c
          JOIN contract_cpv_codes cc ON c.id_contrato = cc.contract_id
          JOIN cpv_codes cp ON cc.cpv_code = cp.code
          WHERE c.data_publicacao >= ${startDate}
            AND c.data_publicacao <= ${endDate}
          GROUP BY cp.code, cp.description
          ORDER BY count DESC
          LIMIT 10
        `
      ]);
      
      return {
        totalAnnouncements,
        totalContracts,
        totalValue: contractStats._sum.precoContratual || 0,
        averageValue: contractStats._avg.precoContratual || 0,
        topEntities,
        topCpvCodes
      };
    }
  },
  
  Announcement: {
    cpvCodes: async (parent) => {
      const codes = await prisma.announcementCpv.findMany({
        where: { announcementId: parent.nAnuncio },
        include: { cpv: true }
      });
      return codes.map(c => c.cpv);
    },
    
    contractTypes: async (parent) => {
      const types = await prisma.announcementContractType.findMany({
        where: { announcementId: parent.nAnuncio },
        include: { contractType: true }
      });
      return types.map(t => t.contractType);
    }
  },
  
  Contract: {
    winners: async (parent) => {
      const winners = await prisma.contractWinner.findMany({
        where: { contractId: parent.idContrato },
        include: { winner: true }
      });
      return winners.map(w => w.winner);
    },
    
    competitors: async (parent) => {
      const competitors = await prisma.contractCompetitor.findMany({
        where: { contractId: parent.idContrato },
        include: { competitor: true }
      });
      return competitors.map(c => c.competitor);
    },
    
    cpvCodes: async (parent) => {
      const codes = await prisma.contractCpv.findMany({
        where: { contractId: parent.idContrato },
        include: { cpv: true }
      });
      return codes.map(c => c.cpv);
    },
    
    contractTypes: async (parent) => {
      const types = await prisma.contractContractType.findMany({
        where: { contractId: parent.idContrato },
        include: { contractType: true }
      });
      return types.map(t => t.contractType);
    }
  }
};

// Helper functions
function buildAnnouncementWhere(filter) {
  const where: any = {};
  
  if (filter.startDate || filter.endDate) {
    where.dataPublicacao = {};
    if (filter.startDate) where.dataPublicacao.gte = filter.startDate;
    if (filter.endDate) where.dataPublicacao.lte = filter.endDate;
  }
  
  if (filter.nifEntidade) {
    where.nifEntidade = filter.nifEntidade;
  }
  
  if (filter.minPrice || filter.maxPrice) {
    where.precoBase = {};
    if (filter.minPrice) where.precoBase.gte = filter.minPrice;
    if (filter.maxPrice) where.precoBase.lte = filter.maxPrice;
  }
  
  if (filter.cpvCode) {
    where.cpvCodes = {
      some: { cpvCode: filter.cpvCode }
    };
  }
  
  return where;
}

function buildContractWhere(filter) {
  const where: any = {};
  
  if (filter.startDate || filter.endDate) {
    where.dataPublicacao = {};
    if (filter.startDate) where.dataPublicacao.gte = filter.startDate;
    if (filter.endDate) where.dataPublicacao.lte = filter.endDate;
  }
  
  if (filter.adjudicanteNif) {
    where.adjudicanteNif = filter.adjudicanteNif;
  }
  
  if (filter.winnerNif) {
    where.winners = {
      some: { winnerNif: filter.winnerNif }
    };
  }
  
  if (filter.minValue || filter.maxValue) {
    where.precoContratual = {};
    if (filter.minValue) where.precoContratual.gte = filter.minValue;
    if (filter.maxValue) where.precoContratual.lte = filter.maxValue;
  }
  
  if (filter.cpvCode) {
    where.cpvCodes = {
      some: { cpvCode: filter.cpvCode }
    };
  }
  
  return where;
}
```

### Week 9: API Server & Authentication

#### 9.1 Create Express Server
Create `backend/src/server.ts`:
```typescript
import express from 'express';
import { ApolloServer } from 'apollo-server-express';
import { typeDefs } from './schema/typeDefs';
import { resolvers } from './resolvers';
import { PrismaClient } from '@prisma/client';
import cors from 'cors';
import helmet from 'helmet';

const prisma = new PrismaClient();

async function startServer() {
  const app = express();
  
  // Security middleware
  app.use(helmet({
    contentSecurityPolicy: false // Allow GraphQL Playground
  }));
  
  // CORS configuration
  app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true
  }));
  
  // Health check endpoint
  app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
  });
  
  // Create Apollo Server
  const server = new ApolloServer({
    typeDefs,
    resolvers,
    context: ({ req }) => {
      // Add authentication context here
      return {
        prisma,
        user: null // Will be populated by auth middleware
      };
    },
    introspection: true,
    playground: process.env.NODE_ENV !== 'production'
  });
  
  await server.start();
  server.applyMiddleware({ app, path: '/graphql' });
  
  const PORT = process.env.PORT || 4000;
  
  app.listen(PORT, () => {
    console.log(`🚀 Server ready at http://localhost:${PORT}${server.graphqlPath}`);
  });
}

startServer().catch(err => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
```

---

## Phase 4: Frontend Application (Weeks 10-12)

### Week 10: Next.js Setup & Landing Page

#### 10.1 Initialize Next.js Project
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app
npm install @apollo/client graphql
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install recharts date-fns
```

#### 10.2 Create Landing Page
Create `frontend/app/page.tsx`:
```typescript
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-blue-50 to-white py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-5xl font-bold mb-6">
              Inteligência em Contratos Públicos
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              Acompanhe oportunidades de negócio no portal BASE em tempo real.
              Receba alertas personalizados e análises de mercado.
            </p>
            <div className="flex gap-4 justify-center">
              <Link href="/register">
                <Button size="lg">Começar Teste Gratuito</Button>
              </Link>
              <Link href="/demo">
                <Button size="lg" variant="outline">Ver Demonstração</Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
      
      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Funcionalidades Principais
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-3">
                Alertas em Tempo Real
              </h3>
              <p className="text-gray-600">
                Receba notificações diárias sobre novas oportunidades 
                relevantes para o seu negócio.
              </p>
            </Card>
            
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-3">
                Análise de Concorrência
              </h3>
              <p className="text-gray-600">
                Acompanhe os seus concorrentes e entenda as suas 
                estratégias de contratação.
              </p>
            </Card>
            
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-3">
                Filtros Inteligentes
              </h3>
              <p className="text-gray-600">
                Configure alertas por região, categoria CPV, valor 
                e tipo de procedimento.
              </p>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}
```

### Week 11-12: Dashboard Implementation

(Due to length constraints, I'll provide the structure for the remaining phases)

---

## Phase 5: Newsletter System (Week 13)

### Components to Build:
1. Email template engine with React Email
2. Queue system with Bull and Redis
3. Personalization engine based on preferences
4. Unsubscribe management
5. Email analytics integration

---

## Phase 6: Testing & Deployment (Weeks 14-15)

### Testing Strategy:
1. Unit tests for all ETL components
2. Integration tests for API
3. E2E tests for critical user flows
4. Load testing for API endpoints
5. Security audit

### Deployment:
1. Docker images for all services
2. Docker Compose for orchestration
3. Environment-specific configurations
4. CI/CD pipeline with GitHub Actions
5. Monitoring with Prometheus/Grafana

---

## Phase 7: Launch & Monitoring (Week 16)

### Launch Checklist:
1. Production environment setup
2. SSL certificates
3. Domain configuration
4. Email service configuration
5. Payment integration (Stripe)
6. Analytics setup (Google Analytics, Mixpanel)
7. Error tracking (Sentry)
8. Backup automation
9. Documentation completion
10. Beta user onboarding

---

## Success Metrics

### Technical Metrics:
- [ ] ETL pipeline runs successfully every 6 hours
- [ ] API response time < 200ms for 95% of requests
- [ ] Database queries optimized (< 100ms)
- [ ] 99.9% uptime achieved
- [ ] All tests passing with > 80% coverage

### Business Metrics:
- [ ] 100+ newsletter subscribers in first month
- [ ] 10% trial-to-paid conversion rate
- [ ] < 5% monthly churn rate
- [ ] Positive user feedback

---

## Risk Mitigation

### Critical Risks:
1. **API Changes**: Implement robust error handling and monitoring
2. **Data Quality**: Comprehensive validation and cleaning
3. **Scaling**: Design for horizontal scaling from day one
4. **Security**: Regular audits and penetration testing

---

## Documentation Requirements

### To Complete:
1. API documentation (GraphQL Playground)
2. User documentation (Help center)
3. Developer documentation (GitHub Wiki)
4. Deployment runbook
5. Incident response procedures

---

## Post-Launch Roadmap

### Month 1-3:
- Mobile app development
- Advanced analytics features
- API for enterprise customers
- Integration with accounting software

### Month 4-6:
- AI-powered recommendations
- Automated bid preparation
- Expansion to Spanish market
- White-label offerings

---

This implementation plan provides a comprehensive roadmap for building the Contrap platform from scratch. Each phase builds upon the previous one, ensuring a solid foundation and iterative development approach.
