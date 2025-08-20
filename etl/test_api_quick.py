#!/usr/bin/env python3
"""
Quick test script for the API client
"""

import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_client import ContrapAPIClient, APIConfig

async def test_announcements():
    """Test fetching announcements for 2025"""
    
    # Use a custom config with appropriate timeout
    config = APIConfig(
        rate_limit=2,      # Lower rate limit for testing
        timeout=120,       # 2 minutes timeout
        max_retries=1      # Just one retry for quick testing
    )
    
    async with ContrapAPIClient(config) as client:
        print("Testing API Client with Year 2025")
        print("="*50)
        
        # Test 1: Fetch announcements for 2025
        print("\n1. Fetching announcements for 2025...")
        announcements = await client.get_announcements(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            year=2025
        )
        
        print(f"✓ Successfully fetched {len(announcements)} announcements")
        
        if announcements:
            # Show first announcement as sample
            first = announcements[0]
            print(f"\nSample announcement:")
            print(f"  - Number: {first.get('nAnuncio', 'N/A')}")
            print(f"  - Entity: {first.get('designacaoEntidade', 'N/A')}")
            print(f"  - Description: {first.get('descricaoAnuncio', 'N/A')[:100]}...")
            print(f"  - Base Price: {first.get('PrecoBase', 'N/A')}")
            print(f"  - Publication Date: {first.get('dataPublicacao', 'N/A')}")
            
            # Show some statistics
            print(f"\nStatistics:")
            print(f"  - Total announcements: {len(announcements)}")
            
            # Count by model
            models = {}
            for ann in announcements:
                model = ann.get('modeloAnuncio', 'Unknown')
                models[model] = models.get(model, 0) + 1
            
            print(f"  - By procurement model:")
            for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    • {model}: {count}")
        
        # Get client statistics
        stats = client.get_statistics()
        print(f"\nClient Statistics:")
        print(f"  - Total requests: {stats['total_requests']}")
        print(f"  - Total errors: {stats['total_errors']}")
        print(f"  - Success rate: {stats['success_rate']:.1f}%")
        
        print("\n" + "="*50)
        print("✓ API Client test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_announcements())
