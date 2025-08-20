"""
Data Fetcher Module
Responsible for fetching data from the Portuguese Government Procurement API
and storing it as raw JSON files for processing.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .api_client import ContrapAPIClient, APIConfig

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches procurement data from the API and stores it as raw JSON files.
    """
    
    def __init__(self, output_dir: Path = None, api_config: APIConfig = None):
        """
        Initialize the DataFetcher.
        
        Args:
            output_dir: Directory to store raw data files
            api_config: API configuration object
        """
        if output_dir is None:
            output_dir = Path("data/raw")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.api_config = api_config or APIConfig()
        
        # Create subdirectories for different data types
        self.announcements_dir = self.output_dir / "announcements"
        self.contracts_dir = self.output_dir / "contracts"
        self.entities_dir = self.output_dir / "entities"
        self.modifications_dir = self.output_dir / "modifications"
        
        for directory in [self.announcements_dir, self.contracts_dir, 
                         self.entities_dir, self.modifications_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _save_to_file(self, data: Any, data_type: str, identifier: str) -> Path:
        """
        Save fetched data to JSON file.
        
        Args:
            data: Data to save
            data_type: Type of data (announcements, contracts, entities, modifications)
            identifier: Unique identifier for the file (e.g., date or year)
        
        Returns:
            Path to the saved file
        """
        # Determine the appropriate directory
        type_to_dir = {
            "announcements": self.announcements_dir,
            "contracts": self.contracts_dir,
            "entities": self.entities_dir,
            "modifications": self.modifications_dir
        }
        
        output_dir = type_to_dir.get(data_type, self.output_dir)
        
        # Create filename
        filename = f"{data_type}_{identifier}.json"
        filepath = output_dir / filename
        
        # Save data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Log based on data structure
        if isinstance(data, list):
            logger.info(f"Saved {len(data)} {data_type} to {filepath}")
        elif isinstance(data, dict) and 'items' in data:
            logger.info(f"Saved {len(data.get('items', []))} {data_type} to {filepath}")
        else:
            logger.info(f"Saved {data_type} data to {filepath}")
        
        return filepath
    
    async def fetch_announcements_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all announcements for a specific year.
        
        Args:
            year: Year to fetch announcements for
        
        Returns:
            List of announcement dictionaries
        """
        logger.info(f"Fetching announcements for year {year}")
        
        async with ContrapAPIClient(self.api_config) as client:
            announcements = await client.get_announcements(year)
        
        # Save to file
        self._save_to_file(announcements, "announcements", str(year))
        
        return announcements
    
    async def fetch_contracts_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all contracts for a specific year.
        
        Args:
            year: Year to fetch contracts for
        
        Returns:
            List of contract dictionaries
        """
        logger.info(f"Fetching contracts for year {year}")
        
        async with ContrapAPIClient(self.api_config) as client:
            contracts = await client.get_contracts(year)
        
        # Save to file
        self._save_to_file(contracts, "contracts", str(year))
        
        return contracts
    
    async def fetch_contract_modifications_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all contract modifications for a specific year.
        
        Args:
            year: Year to fetch modifications for
        
        Returns:
            List of modification dictionaries
        """
        logger.info(f"Fetching contract modifications for year {year}")
        
        async with ContrapAPIClient(self.api_config) as client:
            modifications = await client.get_contract_modifications(year)
        
        # Save to file
        self._save_to_file(modifications, "modifications", str(year))
        
        return modifications
    
    async def fetch_entity(self, nif: str) -> Optional[Dict[str, Any]]:
        """
        Fetch entity information by NIF.
        
        Args:
            nif: Tax identification number
        
        Returns:
            Entity dictionary or None if not found
        """
        logger.info(f"Fetching entity with NIF {nif}")
        
        try:
            async with ContrapAPIClient(self.api_config) as client:
                entity = await client.get_entity(nif)
            
            if entity:
                # Save to file
                self._save_to_file(entity, "entities", nif)
            
            return entity
        except Exception as e:
            logger.error(f"Error fetching entity {nif}: {str(e)}")
            return None
    
    async def fetch_entities_batch(self, nifs: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch multiple entities in batch.
        
        Args:
            nifs: List of NIFs to fetch
        
        Returns:
            Dictionary mapping NIF to entity data
        """
        entities = {}
        
        # Process in smaller batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(nifs), batch_size):
            batch = nifs[i:i + batch_size]
            
            # Fetch entities concurrently within batch
            tasks = [self.fetch_entity(nif) for nif in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for nif, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch entity {nif}: {result}")
                    entities[nif] = None
                else:
                    entities[nif] = result
            
            # Small delay between batches
            if i + batch_size < len(nifs):
                await asyncio.sleep(1)
        
        return entities
    
    async def fetch_historical_data(
        self, 
        start_year: int, 
        end_year: int,
        data_types: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch historical data for a range of years.
        
        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
            data_types: List of data types to fetch 
                       (announcements, contracts, modifications)
                       If None, fetches all types
        
        Returns:
            Dictionary with data type as key and list of records as value
        """
        if data_types is None:
            data_types = ["announcements", "contracts", "modifications"]
        
        all_data = {dtype: [] for dtype in data_types}
        
        for year in range(start_year, end_year + 1):
            logger.info(f"Fetching data for year {year}")
            
            if "announcements" in data_types:
                try:
                    announcements = await self.fetch_announcements_by_year(year)
                    all_data["announcements"].extend(announcements)
                except Exception as e:
                    logger.error(f"Failed to fetch announcements for {year}: {e}")
            
            if "contracts" in data_types:
                try:
                    contracts = await self.fetch_contracts_by_year(year)
                    all_data["contracts"].extend(contracts)
                except Exception as e:
                    logger.error(f"Failed to fetch contracts for {year}: {e}")
            
            if "modifications" in data_types:
                try:
                    modifications = await self.fetch_contract_modifications_by_year(year)
                    all_data["modifications"].extend(modifications)
                except Exception as e:
                    logger.error(f"Failed to fetch modifications for {year}: {e}")
            
            # Delay between years to be respectful to the API
            if year < end_year:
                await asyncio.sleep(2)
        
        logger.info(f"Historical data fetch complete. Total records fetched:")
        for dtype, records in all_data.items():
            logger.info(f"  {dtype}: {len(records)}")
        
        return all_data
    
    async def fetch_daily_update(self, year: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch the latest data for daily updates.
        
        Args:
            year: Year to fetch (defaults to current year)
        
        Returns:
            Dictionary with data type as key and list of records as value
        """
        if year is None:
            year = datetime.now().year
        
        logger.info(f"Fetching daily update for year {year}")
        
        daily_data = {}
        
        try:
            daily_data["announcements"] = await self.fetch_announcements_by_year(year)
        except Exception as e:
            logger.error(f"Failed to fetch announcements: {e}")
            daily_data["announcements"] = []
        
        try:
            daily_data["contracts"] = await self.fetch_contracts_by_year(year)
        except Exception as e:
            logger.error(f"Failed to fetch contracts: {e}")
            daily_data["contracts"] = []
        
        try:
            daily_data["modifications"] = await self.fetch_contract_modifications_by_year(year)
        except Exception as e:
            logger.error(f"Failed to fetch modifications: {e}")
            daily_data["modifications"] = []
        
        return daily_data


async def main():
    """
    Example usage of the DataFetcher.
    """
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize fetcher
    fetcher = DataFetcher()
    
    # Example: Fetch current year's data
    current_year = datetime.now().year
    data = await fetcher.fetch_daily_update(current_year)
    
    print(f"\nFetched data summary for {current_year}:")
    for dtype, records in data.items():
        print(f"  {dtype}: {len(records)} records")
    
    # Example: Fetch specific entity
    # entity = await fetcher.fetch_entity("500000000")  # Example NIF


if __name__ == "__main__":
    asyncio.run(main())
