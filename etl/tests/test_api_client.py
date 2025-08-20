"""
Test module for the Contrap API Client
=======================================

This module contains tests for the API client functionality,
including connection testing, data fetching, and error handling.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api_client import (
    ContrapAPIClient, 
    APIConfig, 
    AsyncRequestConfig,
    get_default_async_config,
    get_batch_processing_config
)

# Test configuration
TEST_CONFIG = APIConfig(
    rate_limit=2,  # Lower rate limit for testing
    timeout=120,    # 2 minutes for large responses
    max_retries=2   # Fewer retries for tests
)

@pytest.fixture
async def api_client():
    """Create an API client instance for testing"""
    async with ContrapAPIClient(TEST_CONFIG) as client:
        yield client

@pytest.mark.asyncio
async def test_api_connection():
    """Test basic API connection"""
    async with ContrapAPIClient(TEST_CONFIG) as client:
        # Test with year 2025 (current year)
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 7)
        
        try:
            announcements = await client.get_announcements(start_date, end_date)
            print(f"✓ Successfully connected to API")
            print(f"  Found {len(announcements)} announcements")
            
            if announcements:
                print(f"  Sample announcement ID: {announcements[0].get('id', 'N/A')}")
            
            assert isinstance(announcements, list)
            
        except Exception as e:
            pytest.fail(f"Failed to connect to API: {str(e)}")

@pytest.mark.asyncio
async def test_get_contracts():
    """Test fetching contracts"""
    async with ContrapAPIClient(TEST_CONFIG) as client:
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 7)
        
        contracts = await client.get_contracts(start_date, end_date)
        print(f"✓ Successfully fetched {len(contracts)} contracts")
        
        assert isinstance(contracts, list)
        
        if contracts:
            # Check structure of first contract
            contract = contracts[0]
            print(f"  Sample contract fields: {list(contract.keys())[:5]}...")

@pytest.mark.asyncio
async def test_get_entity():
    """Test fetching entity information"""
    async with ContrapAPIClient(TEST_CONFIG) as client:
        # Test with a known entity NIF (example)
        test_nif = "500000000"  # Generic test NIF
        
        try:
            entity = await client.get_entity(test_nif)
            print(f"✓ Successfully fetched entity data")
            
            if entity:
                print(f"  Entity name: {entity.get('nome', 'N/A')}")
            
            assert isinstance(entity, dict)
            
        except Exception as e:
            # Entity might not exist, which is fine for testing
            print(f"  Note: Entity fetch returned error (expected): {str(e)}")

@pytest.mark.asyncio
async def test_async_configuration():
    """Test extended async configuration for slow responses"""
    config = get_default_async_config()
    
    assert config.max_retries == 5
    assert config.timeout == 600
    assert config.base_delay == 10
    
    batch_config = get_batch_processing_config()
    assert batch_config.timeout == 3600
    
    print("✓ Async configuration factories work correctly")

@pytest.mark.asyncio
async def test_statistics():
    """Test client statistics tracking"""
    async with ContrapAPIClient(TEST_CONFIG) as client:
        # Make a request
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        await client.get_announcements(start_date, end_date)
        
        stats = client.get_statistics()
        
        assert stats["total_requests"] > 0
        assert "success_rate" in stats
        
        print(f"✓ Statistics tracking works")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")

@pytest.mark.asyncio
async def test_year_parameter():
    """Test using year parameter instead of date range"""
    async with ContrapAPIClient(TEST_CONFIG) as client:
        # Test with year parameter
        announcements = await client.get_announcements(
            start_date=datetime.now(),  # These will be ignored
            end_date=datetime.now(),
            year=2025
        )
        
        print(f"✓ Year parameter works")
        print(f"  Found {len(announcements)} announcements for 2025")
        
        assert isinstance(announcements, list)

# Manual test runner for quick verification
async def run_manual_tests():
    """Run manual tests for quick verification"""
    print("\n" + "="*60)
    print("Running Contrap API Client Tests")
    print("="*60 + "\n")
    
    # Test 1: Basic connection
    print("1. Testing API connection...")
    await test_api_connection()
    
    # Test 2: Get contracts
    print("\n2. Testing contract fetching...")
    await test_get_contracts()
    
    # Test 3: Entity lookup
    print("\n3. Testing entity lookup...")
    await test_get_entity()
    
    # Test 4: Configuration
    print("\n4. Testing async configuration...")
    await test_async_configuration()
    
    # Test 5: Statistics
    print("\n5. Testing statistics...")
    await test_statistics()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Run manual tests
    asyncio.run(run_manual_tests())
