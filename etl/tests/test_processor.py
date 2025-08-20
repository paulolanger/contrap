"""
Tests for the Data Processor module.
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import asyncpg

from etl.src.processor import DataProcessor
from etl.src.validator import DataValidator


class TestDataProcessor:
    """Test suite for DataProcessor class."""
    
    @pytest.fixture
    def db_config(self):
        """Create test database configuration."""
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_password'
        }
    
    @pytest.fixture
    def processor(self, db_config):
        """Create a DataProcessor instance."""
        return DataProcessor(db_config)
    
    @pytest.fixture
    def sample_entity(self):
        """Sample entity data."""
        return {
            'nif': '500000000',
            'designacao': 'Test Entity',
            'morada': 'Test Address',
            'codigoPostal': '1000-000',
            'localidade': 'Lisboa',
            'pais': 'Portugal',
            'email': 'test@example.com',
            'telefone': '+351123456789',
            'website': 'https://example.com',
            'tipoEntidade': 'public'
        }
    
    @pytest.fixture
    def sample_announcement(self):
        """Sample announcement data."""
        return {
            'idAnuncio': 'ANN001',
            'nifEntidade': '500000000',
            'designacaoEntidade': 'Test Entity',
            'objetoContrato': 'Test Contract Object',
            'descricao': 'Test Description',
            'tipoContrato': 'Aquisição de Serviços',
            'tipoProcedimento': 'Concurso público',
            'precoBase': '100000.50',
            'dataPublicacao': '01/01/2024',
            'dataFimProposta': '31/01/2024',
            'dataAberturaPropostas': '01/02/2024',
            'estado': 'active',
            'url': 'https://example.com/announcement',
            'referencia': 'REF001',
            'localExecucao': 'Lisboa',
            'codigoNuts': 'PT171',
            'prazoExecucao': 12,
            'acordoQuadro': False,
            'cpvs': ['12345678-9 - Test CPV']
        }
    
    @pytest.fixture
    def sample_contract(self):
        """Sample contract data."""
        return {
            'idContrato': 'CON001',
            'idAnuncio': 'ANN001',
            'nifEntidade': '500000000',
            'designacaoEntidade': 'Test Entity',
            'nifAdjudicatario': '123456789',
            'designacaoAdjudicatario': 'Test Supplier',
            'objetoContrato': 'Test Contract Object',
            'descricao': 'Test Description',
            'tipoContrato': 'Aquisição de Serviços',
            'tipoProcedimento': 'Concurso público',
            'precoContratual': '95000.00',
            'dataPublicacao': '01/02/2024',
            'dataCelebracaoContrato': '15/02/2024',
            'dataInicioExecucao': '01/03/2024',
            'dataFimExecucao': '28/02/2025',
            'estado': 'active',
            'url': 'https://example.com/contract',
            'referencia': 'REF001',
            'localExecucao': 'Lisboa',
            'codigoNuts': 'PT171',
            'cpvs': ['12345678-9 - Test CPV'],
            'concorrentes': ['987654321-Competitor Company']
        }
    
    @pytest.fixture
    def sample_modification(self):
        """Sample contract modification data."""
        return {
            'idContrato': 'CON001',
            'dataModificacao': '01/06/2024',
            'tipoModificacao': 'value_increase',
            'descricao': 'Contract value increase',
            'valorOriginal': '95000.00',
            'valorNovo': '105000.00',
            'prazoOriginal': '28/02/2025',
            'prazoNovo': '31/03/2025',
            'justificacao': 'Additional requirements'
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self, processor):
        """Test DataProcessor initialization."""
        assert processor.db_config is not None
        assert processor.pool is None
        assert isinstance(processor.validator, DataValidator)
        assert len(processor.processed_announcements) == 0
        assert len(processor.processed_contracts) == 0
        assert len(processor.processed_entities) == 0
    
    @pytest.mark.asyncio
    async def test_pool_management(self, processor):
        """Test connection pool management."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            # Initialize pool
            await processor.initialize_pool()
            assert processor.pool == mock_pool
            mock_create_pool.assert_called_once()
            
            # Close pool
            await processor.close_pool()
            mock_pool.close.assert_called_once()
            assert processor.pool is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, processor):
        """Test async context manager."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            async with processor as p:
                assert p.pool == mock_pool
            
            mock_pool.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_entity_valid(self, processor, sample_entity):
        """Test processing a valid entity."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # Entity doesn't exist
        mock_conn.fetchval.return_value = 1  # Return entity ID
        
        entity_id = await processor.process_entity(sample_entity, mock_conn)
        
        assert entity_id == 1
        assert '500000000' in processor.processed_entities
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_entity_invalid_nif(self, processor):
        """Test processing entity with invalid NIF."""
        mock_conn = AsyncMock()
        invalid_entity = {'nif': 'invalid', 'designacao': 'Test'}
        
        entity_id = await processor.process_entity(invalid_entity, mock_conn)
        
        assert entity_id is None
        mock_conn.fetchrow.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_entity_update_existing(self, processor, sample_entity):
        """Test updating an existing entity."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1}  # Entity exists
        mock_conn.fetchval.return_value = 1
        
        entity_id = await processor.process_entity(sample_entity, mock_conn)
        
        assert entity_id == 1
        # Should call update query (fetchval with UPDATE statement)
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_announcement_valid(self, processor, sample_announcement):
        """Test processing a valid announcement."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # Entity doesn't exist
        mock_conn.fetchval.side_effect = [1, 10]  # Entity ID, then announcement ID
        mock_conn.execute.return_value = None
        
        with patch.object(processor, 'process_entity', return_value=1):
            announcement_id = await processor.process_announcement(sample_announcement, mock_conn)
        
        assert announcement_id == 10
        assert 'ANN001' in processor.processed_announcements
    
    @pytest.mark.asyncio
    async def test_process_announcement_duplicate(self, processor, sample_announcement):
        """Test processing duplicate announcement."""
        mock_conn = AsyncMock()
        processor.processed_announcements.add('ANN001')
        
        announcement_id = await processor.process_announcement(sample_announcement, mock_conn)
        
        assert announcement_id is None
        mock_conn.fetchval.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_announcement_invalid(self, processor):
        """Test processing invalid announcement."""
        mock_conn = AsyncMock()
        invalid_announcement = {'idAnuncio': 'ANN002'}  # Missing required fields
        
        announcement_id = await processor.process_announcement(invalid_announcement, mock_conn)
        
        assert announcement_id is None
    
    @pytest.mark.asyncio
    async def test_process_contract_valid(self, processor, sample_contract):
        """Test processing a valid contract."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # Entities don't exist
        mock_conn.fetchval.side_effect = [1, 2, 10, 20]  # Entity IDs, announcement ID, contract ID
        mock_conn.execute.return_value = None
        
        with patch.object(processor, 'process_entity', side_effect=[1, 2]):
            contract_id = await processor.process_contract(sample_contract, mock_conn)
        
        assert contract_id == 20
        assert 'CON001' in processor.processed_contracts
    
    @pytest.mark.asyncio
    async def test_process_contract_with_competitors(self, processor, sample_contract):
        """Test processing contract with competitors."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_conn.fetchval.side_effect = [1, 2, None, 20, 3]  # Include competitor entity ID
        mock_conn.execute.return_value = None
        
        with patch.object(processor, 'process_entity', side_effect=[1, 2, 3]):
            contract_id = await processor.process_contract(sample_contract, mock_conn)
        
        assert contract_id == 20
        # Should have inserted competitor relationship
        assert mock_conn.execute.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_process_contract_modification(self, processor, sample_modification):
        """Test processing contract modification."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = [10, 1]  # Contract ID, modification ID
        mock_conn.execute.return_value = None
        
        modification_id = await processor.process_contract_modification(
            sample_modification, mock_conn
        )
        
        assert modification_id == 1
        # Should update contract with new value
        mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_contract_modification_no_contract(self, processor, sample_modification):
        """Test processing modification for non-existent contract."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None  # Contract not found
        
        modification_id = await processor.process_contract_modification(
            sample_modification, mock_conn
        )
        
        assert modification_id is None
    
    @pytest.mark.asyncio
    async def test_insert_cpv_code(self, processor):
        """Test CPV code insertion."""
        mock_conn = AsyncMock()
        cpv = {'code': '12345678-9', 'description': 'Test CPV'}
        
        await processor._insert_cpv_code(cpv, mock_conn)
        
        mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_batch(self, processor, sample_announcement, sample_contract):
        """Test batch processing."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.transaction.return_value.__aenter__.return_value = None
        processor.pool = mock_pool
        
        with patch.object(processor, 'process_announcement', return_value=1):
            with patch.object(processor, 'process_contract', return_value=2):
                results = await processor.process_batch(
                    announcements=[sample_announcement],
                    contracts=[sample_contract]
                )
        
        assert results['announcements'] == 1
        assert results['contracts'] == 1
        assert results['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, processor, sample_announcement):
        """Test batch processing with errors."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.transaction.return_value.__aenter__.return_value = None
        processor.pool = mock_pool
        
        with patch.object(processor, 'process_announcement', side_effect=Exception("Test error")):
            results = await processor.process_batch(
                announcements=[sample_announcement]
            )
        
        assert results['announcements'] == 0
        assert results['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_process_from_files(self, processor, tmp_path, sample_announcement, sample_contract):
        """Test processing from JSON files."""
        # Create test JSON files
        announcements_file = tmp_path / "announcements.json"
        contracts_file = tmp_path / "contracts.json"
        
        with open(announcements_file, 'w') as f:
            json.dump([sample_announcement], f)
        
        with open(contracts_file, 'w') as f:
            json.dump({'items': [sample_contract]}, f)
        
        mock_pool = AsyncMock()
        processor.pool = mock_pool
        
        with patch.object(processor, 'process_batch', return_value={'announcements': 1, 'contracts': 1}):
            results = await processor.process_from_files(
                announcements_file=announcements_file,
                contracts_file=contracts_file
            )
        
        assert results['announcements'] == 1
        assert results['contracts'] == 1
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, processor):
        """Test getting database statistics."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        processor.pool = mock_pool
        
        # Mock database responses
        mock_conn.fetchval.side_effect = [
            100,  # total_entities
            50,   # total_announcements
            30,   # total_contracts
            5,    # total_modifications
            datetime(2024, 1, 1),  # earliest_announcement
            datetime(2024, 12, 31),  # latest_announcement
            datetime(2024, 1, 15),  # earliest_contract
            datetime(2024, 12, 15),  # latest_contract
        ]
        
        mock_conn.fetch.side_effect = [
            [{'contract_value': Decimal('10000')}, {'contract_value': Decimal('20000')}],  # contract values
            [],  # top_contracting_entities
            []   # top_suppliers
        ]
        
        stats = await processor.get_statistics()
        
        assert stats['total_entities'] == 100
        assert stats['total_announcements'] == 50
        assert stats['total_contracts'] == 30
        assert stats['total_modifications'] == 5
        assert stats['total_contract_value'] == 30000
        assert stats['average_contract_value'] == 15000
