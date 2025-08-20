"""
Tests for the Data Fetcher module.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from etl.src.fetcher import DataFetcher
from etl.src.api_client import APIConfig


class TestDataFetcher:
    """Test suite for DataFetcher class."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for test output."""
        return tmp_path / "test_output"
    
    @pytest.fixture
    def fetcher(self, temp_dir):
        """Create a DataFetcher instance with test configuration."""
        config = APIConfig(
            base_url="https://test.api",
            access_token="test_token",
            rate_limit=10,
            timeout=30
        )
        return DataFetcher(output_dir=temp_dir, api_config=config)
    
    @pytest.fixture
    def sample_announcements(self):
        """Sample announcement data."""
        return [
            {
                "idAnuncio": "1",
                "nifEntidade": "500000000",
                "designacaoEntidade": "Test Entity",
                "dataPublicacao": "01/01/2024",
                "objectoContrato": "Test Contract"
            },
            {
                "idAnuncio": "2",
                "nifEntidade": "500000001",
                "designacaoEntidade": "Another Entity",
                "dataPublicacao": "02/01/2024",
                "objectoContrato": "Another Contract"
            }
        ]
    
    @pytest.fixture
    def sample_contracts(self):
        """Sample contract data."""
        return [
            {
                "idContrato": "C1",
                "nifEntidade": "500000000",
                "nifAdjudicatario": "123456789",
                "dataPublicacao": "01/01/2024",
                "precoContratual": "10000"
            }
        ]
    
    def test_initialization(self, fetcher, temp_dir):
        """Test DataFetcher initialization."""
        assert fetcher.output_dir == temp_dir
        assert fetcher.announcements_dir.exists()
        assert fetcher.contracts_dir.exists()
        assert fetcher.entities_dir.exists()
        assert fetcher.modifications_dir.exists()
    
    def test_save_to_file(self, fetcher, sample_announcements):
        """Test saving data to file."""
        filepath = fetcher._save_to_file(
            sample_announcements,
            "announcements",
            "2024"
        )
        
        assert filepath.exists()
        assert filepath.name == "announcements_2024.json"
        
        # Verify content
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data == sample_announcements
    
    @pytest.mark.asyncio
    async def test_fetch_announcements_by_year(self, fetcher, sample_announcements):
        """Test fetching announcements for a specific year."""
        # Mock the API client
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_announcements = AsyncMock(return_value=sample_announcements)
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_announcements_by_year(2024)
            
            assert result == sample_announcements
            mock_instance.get_announcements.assert_called_once_with(2024)
            
            # Check file was saved
            expected_file = fetcher.announcements_dir / "announcements_2024.json"
            assert expected_file.exists()
    
    @pytest.mark.asyncio
    async def test_fetch_contracts_by_year(self, fetcher, sample_contracts):
        """Test fetching contracts for a specific year."""
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_contracts = AsyncMock(return_value=sample_contracts)
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_contracts_by_year(2024)
            
            assert result == sample_contracts
            mock_instance.get_contracts.assert_called_once_with(2024)
            
            # Check file was saved
            expected_file = fetcher.contracts_dir / "contracts_2024.json"
            assert expected_file.exists()
    
    @pytest.mark.asyncio
    async def test_fetch_entity(self, fetcher):
        """Test fetching a single entity."""
        sample_entity = {
            "nif": "500000000",
            "designacao": "Test Entity",
            "morada": "Test Address"
        }
        
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_entity = AsyncMock(return_value=sample_entity)
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_entity("500000000")
            
            assert result == sample_entity
            mock_instance.get_entity.assert_called_once_with("500000000")
            
            # Check file was saved
            expected_file = fetcher.entities_dir / "entities_500000000.json"
            assert expected_file.exists()
    
    @pytest.mark.asyncio
    async def test_fetch_entity_error_handling(self, fetcher):
        """Test entity fetching with error handling."""
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_entity = AsyncMock(side_effect=Exception("API Error"))
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_entity("999999999")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_entities_batch(self, fetcher):
        """Test fetching multiple entities in batch."""
        nifs = ["500000000", "500000001", "500000002"]
        
        with patch.object(fetcher, 'fetch_entity') as mock_fetch:
            mock_fetch.side_effect = [
                {"nif": "500000000", "designacao": "Entity 1"},
                {"nif": "500000001", "designacao": "Entity 2"},
                None  # Simulate failure for third entity
            ]
            
            result = await fetcher.fetch_entities_batch(nifs)
            
            assert len(result) == 3
            assert result["500000000"]["designacao"] == "Entity 1"
            assert result["500000001"]["designacao"] == "Entity 2"
            assert result["500000002"] is None
    
    @pytest.mark.asyncio
    async def test_fetch_historical_data(self, fetcher, sample_announcements, sample_contracts):
        """Test fetching historical data for a range of years."""
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_announcements = AsyncMock(return_value=sample_announcements)
            mock_instance.get_contracts = AsyncMock(return_value=sample_contracts)
            mock_instance.get_contract_modifications = AsyncMock(return_value=[])
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_historical_data(
                start_year=2023,
                end_year=2024,
                data_types=["announcements", "contracts"]
            )
            
            assert "announcements" in result
            assert "contracts" in result
            assert len(result["announcements"]) == 4  # 2 years × 2 announcements
            assert len(result["contracts"]) == 2  # 2 years × 1 contract
    
    @pytest.mark.asyncio
    async def test_fetch_daily_update(self, fetcher, sample_announcements, sample_contracts):
        """Test fetching daily update."""
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_announcements = AsyncMock(return_value=sample_announcements)
            mock_instance.get_contracts = AsyncMock(return_value=sample_contracts)
            mock_instance.get_contract_modifications = AsyncMock(return_value=[])
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_daily_update(2024)
            
            assert "announcements" in result
            assert "contracts" in result
            assert "modifications" in result
            assert len(result["announcements"]) == 2
            assert len(result["contracts"]) == 1
            assert len(result["modifications"]) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_daily_update_error_handling(self, fetcher):
        """Test daily update with error handling."""
        with patch('etl.src.fetcher.ContrapAPIClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get_announcements = AsyncMock(side_effect=Exception("API Error"))
            mock_instance.get_contracts = AsyncMock(return_value=[])
            mock_instance.get_contract_modifications = AsyncMock(return_value=[])
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            result = await fetcher.fetch_daily_update(2024)
            
            # Should handle errors gracefully
            assert result["announcements"] == []
            assert result["contracts"] == []
            assert result["modifications"] == []
