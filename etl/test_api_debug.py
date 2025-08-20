#!/usr/bin/env python3
"""
Debug script to test Portuguese Government API access
"""

import requests
import json

def test_api_configurations():
    """Test different API configurations"""
    
    base_url = "https://www.base.gov.pt/APIBase2/GetInfoAnuncio"
    token = "Nmq28lKgTbr05RaFOJNf"
    
    # Test configurations
    tests = [
        {
            "name": "Token in header with underscore",
            "headers": {"_AccessToken": token},
            "params": {"Ano": "2025"}
        },
        {
            "name": "Token in header without underscore",
            "headers": {"AccessToken": token},
            "params": {"Ano": "2025"}
        },
        {
            "name": "Token in params with underscore",
            "headers": {},
            "params": {"_AccessToken": token, "Ano": "2025"}
        },
        {
            "name": "Token in params without underscore",
            "headers": {},
            "params": {"AccessToken": token, "Ano": "2025"}
        },
        {
            "name": "Token in header (Authorization Bearer)",
            "headers": {"Authorization": f"Bearer {token}"},
            "params": {"Ano": "2025"}
        },
        {
            "name": "Token in header (X-Access-Token)",
            "headers": {"X-Access-Token": token},
            "params": {"Ano": "2025"}
        },
        {
            "name": "No token (to see error)",
            "headers": {},
            "params": {"Ano": "2025"}
        }
    ]
    
    for test in tests:
        print(f"\n{'='*60}")
        print(f"Testing: {test['name']}")
        print(f"Headers: {test['headers']}")
        print(f"Params: {test['params']}")
        print('-'*60)
        
        try:
            response = requests.get(
                base_url,
                headers=test['headers'],
                params=test['params'],
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
            
            # Try to parse response
            content = response.text[:500]
            print(f"Response (first 500 chars): {content}")
            
            # Try to parse as JSON
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"✓ Success! Received {len(data)} items")
                elif isinstance(data, dict):
                    print(f"✓ Success! Response keys: {list(data.keys())}")
                else:
                    print(f"✓ Success! Response type: {type(data)}")
            except:
                if "Token is required" in content:
                    print("✗ Failed: Token is required")
                elif "no Params submited" in content:
                    print("✗ Failed: Missing parameters")
                else:
                    print("✗ Failed: Could not parse JSON")
                    
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    print(f"\n{'='*60}")
    print("Testing complete!")

if __name__ == "__main__":
    test_api_configurations()
