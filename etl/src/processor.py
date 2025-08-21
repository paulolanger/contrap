"""
Data Processor Module
Responsible for transforming validated data and inserting it into the PostgreSQL database.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import json

import asyncpg
from asyncpg import Pool, Connection
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .validator import DataValidator

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Process validated procurement data and insert into PostgreSQL database.
    """
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize the DataProcessor.
        
        Args:
            db_config: Database configuration dictionary with keys:
                - host: Database host
                - port: Database port
                - database: Database name
                - user: Database user
                - password: Database password
        """
        self.db_config = db_config
        self.validator = DataValidator()
        self.pool: Optional[Pool] = None
        
        # Track processed records to avoid duplicates
        self.processed_announcements: Set[str] = set()
        self.processed_contracts: Set[str] = set()
        self.processed_entities: Set[str] = set()
    
    async def initialize_pool(self):
        """Initialize the connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                host=self.db_config['host'],
                port=self.db_config.get('port', 5432),
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
    
    async def close_pool(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_pool()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_pool()
    
    async def process_entity(self, entity_data: Dict[str, Any], conn: Connection) -> Optional[int]:
        """
        Process and insert/update an entity.
        
        Args:
            entity_data: Entity data dictionary
            conn: Database connection
        
        Returns:
            Entity ID if successful, None otherwise
        """
        # Validate NIF
        is_valid, clean_nif = self.validator.validate_nif(entity_data.get('nif', ''))
        if not is_valid:
            logger.warning(f"Invalid entity NIF: {entity_data.get('nif')}")
            return None
        
        # Clean the entity data
        entity_data = self.validator.clean_null_values(entity_data)
        
        try:
            # Check if entity exists
            existing = await conn.fetchrow(
                "SELECT id FROM entities WHERE nif = $1",
                clean_nif
            )
            
            if existing:
                # Update existing entity
                entity_id = await conn.fetchval(
                    """
                    UPDATE entities 
                    SET name = COALESCE($2, name),
                        address = COALESCE($3, address),
                        postal_code = COALESCE($4, postal_code),
                        city = COALESCE($5, city),
                        country = COALESCE($6, country),
                        email = COALESCE($7, email),
                        phone = COALESCE($8, phone),
                        website = COALESCE($9, website),
                        entity_type = COALESCE($10, entity_type),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE nif = $1
                    RETURNING id
                    """,
                    clean_nif,
                    entity_data.get('designacao'),
                    entity_data.get('morada'),
                    entity_data.get('codigoPostal'),
                    entity_data.get('localidade'),
                    entity_data.get('pais', 'Portugal'),
                    entity_data.get('email'),
                    entity_data.get('telefone'),
                    entity_data.get('website'),
                    entity_data.get('tipoEntidade')
                )
            else:
                # Insert new entity
                entity_id = await conn.fetchval(
                    """
                    INSERT INTO entities (
                        nif, name, address, postal_code, city, country,
                        email, phone, website, entity_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (nif) DO UPDATE 
                    SET name = EXCLUDED.name,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                    """,
                    clean_nif,
                    entity_data.get('designacao', f"Entity {clean_nif}"),
                    entity_data.get('morada'),
                    entity_data.get('codigoPostal'),
                    entity_data.get('localidade'),
                    entity_data.get('pais', 'Portugal'),
                    entity_data.get('email'),
                    entity_data.get('telefone'),
                    entity_data.get('website'),
                    entity_data.get('tipoEntidade')
                )
            
            self.processed_entities.add(clean_nif)
            return entity_id
            
        except Exception as e:
            logger.error(f"Error processing entity {clean_nif}: {str(e)}")
            return None
    
    async def process_announcement(self, announcement_data: Dict[str, Any], conn: Connection) -> Optional[int]:
        """
        Process and insert an announcement.
        
        Args:
            announcement_data: Announcement data dictionary
            conn: Database connection
        
        Returns:
            Announcement ID if successful, None otherwise
        """
        from .field_mappings import extract_announcement_id, extract_entity_nif
        
        # Clean the data
        announcement_data = self.validator.clean_null_values(announcement_data)
        
        # Extract announcement ID (can be nAnuncio or idAnuncio)
        announcement_id = extract_announcement_id(announcement_data)
        if not announcement_id or announcement_id in self.processed_announcements:
            return None
        
        # Validate the announcement
        is_valid, errors = self.validator.validate_announcement(announcement_data)
        if not is_valid:
            logger.warning(f"Invalid announcement {announcement_id}: {errors}")
            return None
        
        try:
            # Process the contracting entity
            entity_nif = announcement_data.get('nifEntidade')
            entity_id = None
            if entity_nif:
                entity_data = {
                    'nif': entity_nif,
                    'designacao': announcement_data.get('designacaoEntidade')
                }
                entity_id = await self.process_entity(entity_data, conn)
            
            # Parse dates
            publication_date = self.validator.normalize_date(
                announcement_data.get('dataPublicacao')
            )
            
            # Calculate submission deadline from prazoPropostas (days)
            submission_deadline = None
            prazo_dias = announcement_data.get('prazoPropostas') or announcement_data.get('PrazoPropostas')
            if prazo_dias and publication_date:
                try:
                    from datetime import timedelta
                    # Handle string or numeric values
                    if isinstance(prazo_dias, str):
                        prazo_dias = int(prazo_dias.replace(' dias', '').strip())
                    else:
                        prazo_dias = int(prazo_dias)
                    submission_deadline = publication_date + timedelta(days=prazo_dias)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not calculate submission deadline: {e}")
                    submission_deadline = None
            
            # These fields are not provided by the API
            opening_date = None  # API doesn't provide dataAberturaPropostas
            
            # Parse amount (handle case variations)
            base_price = self.validator.normalize_amount(
                announcement_data.get('precoBase') or 
                announcement_data.get('PrecoBase') or 
                announcement_data.get('valorBase')
            )
            
            # Normalize contract type (can be tiposContrato array or tipoContrato string)
            contract_types = announcement_data.get('tiposContrato', [])
            if contract_types and isinstance(contract_types, list) and len(contract_types) > 0:
                contract_type = self.validator.normalize_contract_type(contract_types[0])
            else:
                contract_type = self.validator.normalize_contract_type(
                    announcement_data.get('tipoContrato')
                )
            
            # Insert announcement
            db_announcement_id = await conn.fetchval(
                """
                INSERT INTO announcements (
                    external_id, entity_id, title, description,
                    contract_type, procedure_type, base_price,
                    publication_date, submission_deadline, opening_date,
                    status, url, reference, location,
                    nuts_code, duration_months, is_framework,
                    is_dynamic_purchasing, allows_electronic_submission,
                    requires_electronic_submission
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (external_id) DO UPDATE
                SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                announcement_id,
                entity_id,
                announcement_data.get('descricaoAnuncio') or announcement_data.get('objetoContrato'),  # title
                announcement_data.get('descricao') or announcement_data.get('descricaoAnuncio'),  # description
                contract_type,
                announcement_data.get('tipoProcedimento') or announcement_data.get('tipoprocedimento') or announcement_data.get('modeloAnuncio'),  # procedure_type
                base_price,
                publication_date,
                submission_deadline,
                opening_date,
                announcement_data.get('estado', 'active'),
                announcement_data.get('url'),
                announcement_data.get('referencia'),  # reference
                announcement_data.get('localExecucao'),  # location
                announcement_data.get('codigoNuts'),  # nuts_code
                self._parse_duration_months(announcement_data.get('prazoExecucao')),  # duration_months
                announcement_data.get('acordoQuadro', False),
                announcement_data.get('sistemaAquisicaoDinamico', False),
                announcement_data.get('permitePropostasEletronicas', False),
                announcement_data.get('obrigaPropostasEletronicas', False)
            )
            
            # Process CPV codes (can be CPVs or cpvs)
            cpv_list = announcement_data.get('CPVs', announcement_data.get('cpvs', []))
            if cpv_list and db_announcement_id:
                cpv_data = self.validator.extract_cpv_codes(cpv_list)
                for cpv in cpv_data:
                    await self._insert_cpv_code(cpv, conn)
                    await conn.execute(
                        """
                        INSERT INTO announcement_cpv (announcement_id, cpv_code)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        db_announcement_id,
                        cpv['code']
                    )
            
            self.processed_announcements.add(announcement_id)
            return db_announcement_id
            
        except Exception as e:
            logger.error(f"Error processing announcement {announcement_id}: {str(e)}")
            return None
    
    async def process_contract(self, contract_data: Dict[str, Any], conn: Connection) -> Optional[int]:
        """
        Process and insert a contract.
        
        Args:
            contract_data: Contract data dictionary
            conn: Database connection
        
        Returns:
            Contract ID if successful, None otherwise
        """
        from .field_mappings import extract_contract_id, extract_contract_entity_nif, extract_contract_supplier_nif
        
        # Clean the data
        contract_data = self.validator.clean_null_values(contract_data)
        
        # Extract contract ID (can be idContrato or idcontrato)
        contract_id = extract_contract_id(contract_data)
        if not contract_id or contract_id in self.processed_contracts:
            return None
        
        # Validate the contract
        is_valid, errors = self.validator.validate_contract(contract_data)
        if not is_valid:
            logger.warning(f"Invalid contract {contract_id}: {errors}")
            return None
        
        try:
            # Process entities
            entity_id = None
            supplier_id = None
            
            # Contracting entity - extract NIF from adjudicante field if needed
            entity_nif = extract_contract_entity_nif(contract_data)
            if entity_nif:
                # Extract entity name from adjudicante field
                entity_name = None
                if 'adjudicante' in contract_data:
                    adj = contract_data['adjudicante']
                    if isinstance(adj, list) and len(adj) > 0 and ' - ' in adj[0]:
                        entity_name = adj[0].split(' - ', 1)[1].strip()
                
                entity_data = {
                    'nif': entity_nif,
                    'designacao': entity_name or contract_data.get('designacaoEntidade')
                }
                entity_id = await self.process_entity(entity_data, conn)
            
            # Supplier entity - extract from adjudicatarios field if needed
            supplier_nif = extract_contract_supplier_nif(contract_data)
            if supplier_nif:
                # Extract supplier name from adjudicatarios field
                supplier_name = None
                if 'adjudicatarios' in contract_data:
                    adj = contract_data['adjudicatarios']
                    if isinstance(adj, list) and len(adj) > 0 and ' - ' in adj[0]:
                        supplier_name = adj[0].split(' - ', 1)[1].strip()
                
                supplier_data = {
                    'nif': supplier_nif,
                    'designacao': supplier_name or contract_data.get('designacaoAdjudicatario')
                }
                supplier_id = await self.process_entity(supplier_data, conn)
            
            # Link announcement if exists (check both idAnuncio and nAnuncio)
            announcement_id = None
            ann_ref = contract_data.get('idAnuncio') or contract_data.get('nAnuncio')
            if ann_ref:
                announcement_id = await conn.fetchval(
                    "SELECT id FROM announcements WHERE external_id = $1",
                    str(ann_ref)
                )
            
            # Parse dates
            publication_date = self.validator.normalize_date(
                contract_data.get('dataPublicacao')
            )
            signature_date = self.validator.normalize_date(
                contract_data.get('dataCelebracaoContrato')
            )
            start_date = self.validator.normalize_date(
                contract_data.get('dataInicioExecucao')
            )
            end_date = self.validator.normalize_date(
                contract_data.get('dataFimExecucao')
            )
            
            # Parse amounts
            contract_value = self.validator.normalize_amount(
                contract_data.get('precoContratual')
            )
            
            # Normalize contract type (handle list or string)
            contract_types = contract_data.get('tipoContrato', [])
            if isinstance(contract_types, list) and len(contract_types) > 0:
                contract_type = self.validator.normalize_contract_type(contract_types[0])
            elif contract_types and not isinstance(contract_types, list):
                contract_type = self.validator.normalize_contract_type(contract_types)
            else:
                contract_type = None
            
            # Insert contract
            db_contract_id = await conn.fetchval(
                """
                INSERT INTO contracts (
                    external_id, announcement_id, entity_id, supplier_id,
                    title, description, contract_type, procedure_type,
                    contract_value, publication_date, signature_date,
                    start_date, end_date, status, url, reference,
                    location, nuts_code, is_framework, observations
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (external_id) DO UPDATE
                SET contract_value = EXCLUDED.contract_value,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                contract_id,
                announcement_id,
                entity_id,
                supplier_id,
                contract_data.get('objectoContrato') or contract_data.get('objetoContrato'),
                contract_data.get('descContrato') or contract_data.get('descricao'),
                contract_type,
                contract_data.get('tipoprocedimento') or contract_data.get('tipoProcedimento'),  # Handle case variations
                contract_value,
                publication_date,
                signature_date,
                start_date,
                end_date,
                contract_data.get('estado', 'active'),
                contract_data.get('url'),
                contract_data.get('referencia'),
                # Handle localExecucao which can be a list
                ', '.join(contract_data.get('localExecucao', [])) if isinstance(contract_data.get('localExecucao'), list) else contract_data.get('localExecucao'),
                contract_data.get('codigoNuts'),
                contract_data.get('acordoQuadro', False),
                contract_data.get('observacoes')
            )
            
            # Process CPV codes (can be cpv or cpvs)
            cpv_list = contract_data.get('cpv', contract_data.get('cpvs', []))
            if cpv_list and db_contract_id:
                cpv_data = self.validator.extract_cpv_codes(cpv_list)
                for cpv in cpv_data:
                    await self._insert_cpv_code(cpv, conn)
                    await conn.execute(
                        """
                        INSERT INTO contract_cpv (contract_id, cpv_code)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        db_contract_id,
                        cpv['code']
                    )
            
            # Process competitors if available
            competitors_list = contract_data.get('concorrentes', [])
            if competitors_list and db_contract_id:
                competitors = self.validator.parse_competitors(competitors_list)
                for competitor in competitors:
                    # Create entity for competitor
                    comp_id = None
                    if competitor.get('nif'):
                        comp_id = await self.process_entity(
                            {
                                'nif': competitor['nif'],
                                'designacao': competitor.get('name')
                            },
                            conn
                        )
                    
                    if comp_id:
                        await conn.execute(
                            """
                            INSERT INTO contract_competitors (
                                contract_id, entity_id, name, nif
                            ) VALUES ($1, $2, $3, $4)
                            ON CONFLICT DO NOTHING
                            """,
                            db_contract_id,
                            comp_id,
                            competitor.get('name'),
                            competitor.get('nif')
                        )
            
            self.processed_contracts.add(contract_id)
            return db_contract_id
            
        except Exception as e:
            logger.error(f"Error processing contract {contract_id}: {str(e)}")
            return None
    
    async def process_contract_modification(
        self, 
        modification_data: Dict[str, Any], 
        conn: Connection
    ) -> Optional[int]:
        """
        Process and insert a contract modification.
        
        Args:
            modification_data: Modification data dictionary
            conn: Database connection
        
        Returns:
            Modification ID if successful, None otherwise
        """
        # Clean the data
        modification_data = self.validator.clean_null_values(modification_data)
        
        try:
            # Find the contract
            contract_id = modification_data.get('idContrato')
            if not contract_id:
                return None
            
            db_contract_id = await conn.fetchval(
                "SELECT id FROM contracts WHERE external_id = $1",
                contract_id
            )
            
            if not db_contract_id:
                logger.warning(f"Contract not found for modification: {contract_id}")
                return None
            
            # Parse dates
            modification_date = self.validator.normalize_date(
                modification_data.get('dataModificacao')
            )
            
            # Parse amounts
            original_value = self.validator.normalize_amount(
                modification_data.get('valorOriginal')
            )
            new_value = self.validator.normalize_amount(
                modification_data.get('valorNovo')
            )
            
            # Insert modification
            modification_id = await conn.fetchval(
                """
                INSERT INTO contract_modifications (
                    contract_id, modification_date, modification_type,
                    description, original_value, new_value,
                    original_deadline, new_deadline, justification
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                db_contract_id,
                modification_date or datetime.now(),
                modification_data.get('tipoModificacao', 'other'),
                modification_data.get('descricao'),
                original_value,
                new_value,
                self.validator.normalize_date(modification_data.get('prazoOriginal')),
                self.validator.normalize_date(modification_data.get('prazoNovo')),
                modification_data.get('justificacao')
            )
            
            # Update contract if new value is provided
            if new_value:
                await conn.execute(
                    """
                    UPDATE contracts 
                    SET contract_value = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    db_contract_id,
                    new_value
                )
            
            return modification_id
            
        except Exception as e:
            logger.error(f"Error processing contract modification: {str(e)}")
            return None
    
    def _parse_duration_months(self, prazo_str: Optional[str]) -> Optional[int]:
        """
        Parse duration string to months.
        
        Args:
            prazo_str: Duration string like "12 meses", "2 anos", "90 dias"
        
        Returns:
            Duration in months or None
        """
        if not prazo_str:
            return None
        
        try:
            prazo_str = str(prazo_str).lower().strip()
            
            # Try to extract number
            import re
            number_match = re.search(r'(\d+)', prazo_str)
            if not number_match:
                return None
            
            number = int(number_match.group(1))
            
            # Convert based on unit
            if 'ano' in prazo_str:
                return number * 12
            elif 'mes' in prazo_str or 'mês' in prazo_str:
                return number
            elif 'dia' in prazo_str:
                return max(1, number // 30)  # Approximate days to months
            elif 'semana' in prazo_str:
                return max(1, number * 7 // 30)  # Approximate weeks to months
            else:
                # If no unit specified, assume months
                return number
        except (ValueError, AttributeError):
            return None
    
    async def _insert_cpv_code(self, cpv: Dict[str, str], conn: Connection):
        """
        Insert or update a CPV code.
        
        Args:
            cpv: CPV dictionary with 'code' and optional 'description'
            conn: Database connection
        """
        try:
            await conn.execute(
                """
                INSERT INTO cpv_codes (code, description)
                VALUES ($1, $2)
                ON CONFLICT (code) DO UPDATE
                SET description = COALESCE(EXCLUDED.description, cpv_codes.description)
                """,
                cpv['code'],
                cpv.get('description')
            )
        except Exception as e:
            logger.error(f"Error inserting CPV code {cpv['code']}: {str(e)}")
    
    async def process_batch(
        self,
        announcements: List[Dict[str, Any]] = None,
        contracts: List[Dict[str, Any]] = None,
        modifications: List[Dict[str, Any]] = None,
        entities: List[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """
        Process batches of different data types.
        
        Args:
            announcements: List of announcement dictionaries
            contracts: List of contract dictionaries
            modifications: List of modification dictionaries
            entities: List of entity dictionaries
        
        Returns:
            Dictionary with counts of processed records
        """
        results = {
            'announcements': 0,
            'contracts': 0,
            'modifications': 0,
            'entities': 0,
            'errors': 0
        }
        
        async with self.pool.acquire() as conn:
            # Process entities first (without transaction for batch)
            if entities:
                for entity in entities:
                    try:
                        async with conn.transaction():
                            entity_id = await self.process_entity(entity, conn)
                            if entity_id:
                                results['entities'] += 1
                    except Exception as e:
                        logger.error(f"Error processing entity: {e}")
                        results['errors'] += 1
                
            # Process announcements (each in its own transaction)
            if announcements:
                for announcement in announcements:
                    try:
                        async with conn.transaction():
                            ann_id = await self.process_announcement(announcement, conn)
                            if ann_id:
                                results['announcements'] += 1
                    except Exception as e:
                        logger.error(f"Error processing announcement: {e}")
                        results['errors'] += 1
                
            # Process contracts (each in its own transaction)
            if contracts:
                for contract in contracts:
                    try:
                        async with conn.transaction():
                            contract_id = await self.process_contract(contract, conn)
                            if contract_id:
                                results['contracts'] += 1
                    except Exception as e:
                        logger.error(f"Error processing contract: {e}")
                        results['errors'] += 1
                
            # Process modifications (each in its own transaction)
            if modifications:
                for modification in modifications:
                    try:
                        async with conn.transaction():
                            mod_id = await self.process_contract_modification(modification, conn)
                            if mod_id:
                                results['modifications'] += 1
                    except Exception as e:
                        logger.error(f"Error processing modification: {e}")
                        results['errors'] += 1
        
        logger.info(f"Batch processing complete: {results}")
        return results
    
    async def process_from_files(
        self,
        announcements_file: Path = None,
        contracts_file: Path = None,
        modifications_file: Path = None
    ) -> Dict[str, int]:
        """
        Process data from JSON files.
        
        Args:
            announcements_file: Path to announcements JSON file
            contracts_file: Path to contracts JSON file
            modifications_file: Path to modifications JSON file
        
        Returns:
            Dictionary with counts of processed records
        """
        announcements = []
        contracts = []
        modifications = []
        
        # Load announcements
        if announcements_file and announcements_file.exists():
            with open(announcements_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    announcements = data
                elif isinstance(data, dict) and 'items' in data:
                    announcements = data['items']
            logger.info(f"Loaded {len(announcements)} announcements from {announcements_file}")
        
        # Load contracts
        if contracts_file and contracts_file.exists():
            with open(contracts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    contracts = data
                elif isinstance(data, dict) and 'items' in data:
                    contracts = data['items']
            logger.info(f"Loaded {len(contracts)} contracts from {contracts_file}")
        
        # Load modifications
        if modifications_file and modifications_file.exists():
            with open(modifications_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    modifications = data
                elif isinstance(data, dict) and 'items' in data:
                    modifications = data['items']
            logger.info(f"Loaded {len(modifications)} modifications from {modifications_file}")
        
        # Process the data
        return await self.process_batch(
            announcements=announcements,
            contracts=contracts,
            modifications=modifications
        )
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with various statistics
        """
        async with self.pool.acquire() as conn:
            stats = {}
            
            # Count records
            stats['total_entities'] = await conn.fetchval(
                "SELECT COUNT(*) FROM entities"
            )
            stats['total_announcements'] = await conn.fetchval(
                "SELECT COUNT(*) FROM announcements"
            )
            stats['total_contracts'] = await conn.fetchval(
                "SELECT COUNT(*) FROM contracts"
            )
            stats['total_modifications'] = await conn.fetchval(
                "SELECT COUNT(*) FROM contract_modifications"
            )
            
            # Get date ranges
            stats['earliest_announcement'] = await conn.fetchval(
                "SELECT MIN(publication_date) FROM announcements"
            )
            stats['latest_announcement'] = await conn.fetchval(
                "SELECT MAX(publication_date) FROM announcements"
            )
            stats['earliest_contract'] = await conn.fetchval(
                "SELECT MIN(signature_date) FROM contracts WHERE signature_date IS NOT NULL"
            )
            stats['latest_contract'] = await conn.fetchval(
                "SELECT MAX(signature_date) FROM contracts WHERE signature_date IS NOT NULL"
            )
            
            # Get value statistics
            contract_values = await conn.fetch(
                "SELECT contract_value FROM contracts WHERE contract_value IS NOT NULL"
            )
            if contract_values:
                values = [float(row['contract_value']) for row in contract_values]
                stats['total_contract_value'] = sum(values)
                stats['average_contract_value'] = sum(values) / len(values)
                stats['min_contract_value'] = min(values)
                stats['max_contract_value'] = max(values)
            
            # Top entities by number of contracts
            stats['top_contracting_entities'] = await conn.fetch(
                """
                SELECT e.name, e.nif, COUNT(c.id) as contract_count
                FROM entities e
                JOIN contracts c ON e.id = c.entity_id
                GROUP BY e.id, e.name, e.nif
                ORDER BY contract_count DESC
                LIMIT 10
                """
            )
            
            stats['top_suppliers'] = await conn.fetch(
                """
                SELECT e.name, e.nif, COUNT(c.id) as contract_count,
                       SUM(c.contract_value) as total_value
                FROM entities e
                JOIN contracts c ON e.id = c.supplier_id
                WHERE c.contract_value IS NOT NULL
                GROUP BY e.id, e.name, e.nif
                ORDER BY total_value DESC
                LIMIT 10
                """
            )
            
            return stats


async def main():
    """
    Example usage of the DataProcessor.
    """
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'contrap'),
        'user': os.getenv('DB_USER', 'contrap'),
        'password': os.getenv('DB_PASSWORD', 'contrap')
    }
    
    # Initialize processor
    async with DataProcessor(db_config) as processor:
        # Example: Process files from data/raw directory
        data_dir = Path('data/raw')
        
        if data_dir.exists():
            # Find latest files
            announcements_files = list(data_dir.glob('announcements/*.json'))
            contracts_files = list(data_dir.glob('contracts/*.json'))
            
            if announcements_files or contracts_files:
                latest_announcements = sorted(announcements_files)[-1] if announcements_files else None
                latest_contracts = sorted(contracts_files)[-1] if contracts_files else None
                
                results = await processor.process_from_files(
                    announcements_file=latest_announcements,
                    contracts_file=latest_contracts
                )
                
                print(f"\nProcessing results:")
                for key, value in results.items():
                    print(f"  {key}: {value}")
        
        # Get statistics
        stats = await processor.get_statistics()
        print(f"\nDatabase statistics:")
        print(f"  Total entities: {stats.get('total_entities', 0)}")
        print(f"  Total announcements: {stats.get('total_announcements', 0)}")
        print(f"  Total contracts: {stats.get('total_contracts', 0)}")
        print(f"  Total modifications: {stats.get('total_modifications', 0)}")
        
        if stats.get('total_contract_value'):
            print(f"  Total contract value: €{stats['total_contract_value']:,.2f}")
            print(f"  Average contract value: €{stats['average_contract_value']:,.2f}")


if __name__ == "__main__":
    asyncio.run(main())
