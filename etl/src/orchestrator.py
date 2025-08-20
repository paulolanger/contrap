"""
ETL Orchestrator Module
Coordinates the entire ETL pipeline flow from data fetching to database insertion.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import json
import traceback

from dotenv import load_dotenv

from .api_client import APIConfig
from .fetcher import DataFetcher
from .validator import DataValidator, validate_batch
from .processor import DataProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    FETCHING = "fetching"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class PipelineMetrics:
    """Track pipeline execution metrics."""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.fetched_counts: Dict[str, int] = {}
        self.validated_counts: Dict[str, int] = {}
        self.processed_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        self.status: PipelineStatus = PipelineStatus.IDLE
        
    def start(self):
        """Mark pipeline start."""
        self.start_time = datetime.now()
        self.status = PipelineStatus.FETCHING
        
    def complete(self, status: PipelineStatus = PipelineStatus.COMPLETED):
        """Mark pipeline completion."""
        self.end_time = datetime.now()
        self.status = status
        
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate pipeline duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration.total_seconds() if self.duration else None,
            'status': self.status.value,
            'fetched': self.fetched_counts,
            'validated': self.validated_counts,
            'processed': self.processed_counts,
            'errors': self.error_counts,
            'total_fetched': sum(self.fetched_counts.values()),
            'total_validated': sum(self.validated_counts.values()),
            'total_processed': sum(self.processed_counts.values()),
            'total_errors': sum(self.error_counts.values())
        }


class ETLOrchestrator:
    """
    Main orchestrator for the ETL pipeline.
    Coordinates fetching, validation, and processing of procurement data.
    """
    
    def __init__(
        self,
        api_config: APIConfig = None,
        db_config: Dict[str, Any] = None,
        data_dir: Path = None,
        enable_cache: bool = True
    ):
        """
        Initialize the ETL Orchestrator.
        
        Args:
            api_config: API configuration
            db_config: Database configuration
            data_dir: Base directory for data storage
            enable_cache: Whether to cache fetched data
        """
        # Load environment variables
        load_dotenv()
        
        # Configure API
        self.api_config = api_config or APIConfig()
        
        # Configure database
        self.db_config = db_config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'contrap'),
            'user': os.getenv('DB_USER', 'contrap'),
            'password': os.getenv('DB_PASSWORD', 'contrap')
        }
        
        # Configure data directory
        self.data_dir = data_dir or Path('data')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup subdirectories
        self.raw_dir = self.data_dir / 'raw'
        self.validated_dir = self.data_dir / 'validated'
        self.processed_dir = self.data_dir / 'processed'
        self.error_dir = self.data_dir / 'errors'
        
        for directory in [self.raw_dir, self.validated_dir, 
                          self.processed_dir, self.error_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.fetcher = DataFetcher(output_dir=self.raw_dir, api_config=self.api_config)
        self.validator = DataValidator()
        self.processor = DataProcessor(self.db_config)
        
        # Configuration
        self.enable_cache = enable_cache
        
        # Metrics
        self.metrics = PipelineMetrics()
        
    async def fetch_data(
        self,
        year: int,
        data_types: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch data from the API.
        
        Args:
            year: Year to fetch data for
            data_types: Types of data to fetch (announcements, contracts, modifications)
        
        Returns:
            Dictionary with fetched data
        """
        logger.info(f"Starting data fetch for year {year}")
        self.metrics.status = PipelineStatus.FETCHING
        
        if data_types is None:
            data_types = ['announcements', 'contracts', 'modifications']
        
        fetched_data = {}
        
        try:
            # Check cache first if enabled
            if self.enable_cache:
                cached_data = self._load_cached_data(year, data_types)
                if cached_data:
                    logger.info(f"Using cached data for year {year}")
                    for dtype, data in cached_data.items():
                        self.metrics.fetched_counts[dtype] = len(data)
                    return cached_data
            
            # Fetch from API
            if 'announcements' in data_types:
                try:
                    announcements = await self.fetcher.fetch_announcements_by_year(year)
                    fetched_data['announcements'] = announcements
                    self.metrics.fetched_counts['announcements'] = len(announcements)
                    logger.info(f"Fetched {len(announcements)} announcements")
                except Exception as e:
                    logger.error(f"Error fetching announcements: {e}")
                    self.metrics.error_counts['fetch_announcements'] = 1
                    fetched_data['announcements'] = []
            
            if 'contracts' in data_types:
                try:
                    contracts = await self.fetcher.fetch_contracts_by_year(year)
                    fetched_data['contracts'] = contracts
                    self.metrics.fetched_counts['contracts'] = len(contracts)
                    logger.info(f"Fetched {len(contracts)} contracts")
                except Exception as e:
                    logger.error(f"Error fetching contracts: {e}")
                    self.metrics.error_counts['fetch_contracts'] = 1
                    fetched_data['contracts'] = []
            
            if 'modifications' in data_types:
                try:
                    modifications = await self.fetcher.fetch_contract_modifications_by_year(year)
                    fetched_data['modifications'] = modifications
                    self.metrics.fetched_counts['modifications'] = len(modifications)
                    logger.info(f"Fetched {len(modifications)} modifications")
                except Exception as e:
                    logger.error(f"Error fetching modifications: {e}")
                    self.metrics.error_counts['fetch_modifications'] = 1
                    fetched_data['modifications'] = []
            
            return fetched_data
            
        except Exception as e:
            logger.error(f"Critical error during data fetch: {e}")
            self.metrics.error_counts['fetch_critical'] = 1
            raise
    
    def validate_data(
        self,
        data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Tuple[List[Dict], List[Dict]]]:
        """
        Validate fetched data.
        
        Args:
            data: Dictionary with data to validate
        
        Returns:
            Dictionary with valid and invalid records for each data type
        """
        logger.info("Starting data validation")
        self.metrics.status = PipelineStatus.VALIDATING
        
        validated_data = {}
        
        # Validate announcements
        if 'announcements' in data:
            try:
                valid, invalid = validate_batch(data['announcements'], 'announcement')
                validated_data['announcements'] = (valid, invalid)
                self.metrics.validated_counts['announcements'] = len(valid)
                self.metrics.error_counts['invalid_announcements'] = len(invalid)
                logger.info(f"Validated announcements: {len(valid)} valid, {len(invalid)} invalid")
                
                # Save invalid records for review
                if invalid:
                    self._save_invalid_records(invalid, 'announcements')
                    
            except Exception as e:
                logger.error(f"Error validating announcements: {e}")
                self.metrics.error_counts['validate_announcements'] = 1
                validated_data['announcements'] = ([], data['announcements'])
        
        # Validate contracts
        if 'contracts' in data:
            try:
                valid, invalid = validate_batch(data['contracts'], 'contract')
                validated_data['contracts'] = (valid, invalid)
                self.metrics.validated_counts['contracts'] = len(valid)
                self.metrics.error_counts['invalid_contracts'] = len(invalid)
                logger.info(f"Validated contracts: {len(valid)} valid, {len(invalid)} invalid")
                
                # Save invalid records for review
                if invalid:
                    self._save_invalid_records(invalid, 'contracts')
                    
            except Exception as e:
                logger.error(f"Error validating contracts: {e}")
                self.metrics.error_counts['validate_contracts'] = 1
                validated_data['contracts'] = ([], data['contracts'])
        
        # Modifications don't have specific validation yet, pass through
        if 'modifications' in data:
            validated_data['modifications'] = (data['modifications'], [])
            self.metrics.validated_counts['modifications'] = len(data['modifications'])
        
        return validated_data
    
    async def process_data(
        self,
        validated_data: Dict[str, Tuple[List[Dict], List[Dict]]]
    ) -> Dict[str, int]:
        """
        Process validated data and insert into database.
        
        Args:
            validated_data: Dictionary with validated data
        
        Returns:
            Dictionary with processing results
        """
        logger.info("Starting data processing")
        self.metrics.status = PipelineStatus.PROCESSING
        
        results = {
            'announcements': 0,
            'contracts': 0,
            'modifications': 0,
            'entities': 0,
            'errors': 0
        }
        
        try:
            async with self.processor as processor:
                # Extract valid data
                announcements = validated_data.get('announcements', ([], []))[0]
                contracts = validated_data.get('contracts', ([], []))[0]
                modifications = validated_data.get('modifications', ([], []))[0]
                
                # Process in batches to avoid memory issues
                batch_size = 100
                
                # Process announcements in batches
                for i in range(0, len(announcements), batch_size):
                    batch = announcements[i:i + batch_size]
                    batch_results = await processor.process_batch(announcements=batch)
                    results['announcements'] += batch_results['announcements']
                    results['errors'] += batch_results['errors']
                    logger.info(f"Processed announcement batch {i//batch_size + 1}")
                
                # Process contracts in batches
                for i in range(0, len(contracts), batch_size):
                    batch = contracts[i:i + batch_size]
                    batch_results = await processor.process_batch(contracts=batch)
                    results['contracts'] += batch_results['contracts']
                    results['errors'] += batch_results['errors']
                    logger.info(f"Processed contract batch {i//batch_size + 1}")
                
                # Process modifications in batches
                for i in range(0, len(modifications), batch_size):
                    batch = modifications[i:i + batch_size]
                    batch_results = await processor.process_batch(modifications=batch)
                    results['modifications'] += batch_results['modifications']
                    results['errors'] += batch_results['errors']
                    logger.info(f"Processed modification batch {i//batch_size + 1}")
                
                # Update metrics
                self.metrics.processed_counts.update(results)
                
                # Get and log statistics
                stats = await processor.get_statistics()
                logger.info(f"Database statistics after processing:")
                logger.info(f"  Total entities: {stats.get('total_entities', 0)}")
                logger.info(f"  Total announcements: {stats.get('total_announcements', 0)}")
                logger.info(f"  Total contracts: {stats.get('total_contracts', 0)}")
                
        except Exception as e:
            logger.error(f"Critical error during data processing: {e}")
            self.metrics.error_counts['process_critical'] = 1
            raise
        
        return results
    
    async def run_pipeline(
        self,
        year: int = None,
        data_types: List[str] = None,
        skip_fetch: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline.
        
        Args:
            year: Year to process (defaults to current year)
            data_types: Types of data to process
            skip_fetch: Skip fetching and use existing raw data
        
        Returns:
            Pipeline execution results
        """
        if year is None:
            year = datetime.now().year
        
        logger.info(f"Starting ETL pipeline for year {year}")
        self.metrics.start()
        
        try:
            # Step 1: Fetch data
            if skip_fetch:
                logger.info("Skipping fetch, loading from raw data directory")
                fetched_data = self._load_raw_data(year, data_types)
            else:
                fetched_data = await self.fetch_data(year, data_types)
            
            if not fetched_data or all(len(v) == 0 for v in fetched_data.values()):
                logger.warning("No data fetched, stopping pipeline")
                self.metrics.complete(PipelineStatus.COMPLETED)
                return self.metrics.to_dict()
            
            # Step 2: Validate data
            validated_data = self.validate_data(fetched_data)
            
            # Step 3: Process data
            processing_results = await self.process_data(validated_data)
            
            # Determine final status
            if self.metrics.error_counts:
                if self.metrics.processed_counts:
                    self.metrics.complete(PipelineStatus.PARTIAL)
                else:
                    self.metrics.complete(PipelineStatus.FAILED)
            else:
                self.metrics.complete(PipelineStatus.COMPLETED)
            
            # Save pipeline report
            self._save_pipeline_report()
            
            logger.info(f"Pipeline completed with status: {self.metrics.status.value}")
            logger.info(f"Duration: {self.metrics.duration}")
            
            return self.metrics.to_dict()
            
        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}")
            logger.error(traceback.format_exc())
            self.metrics.complete(PipelineStatus.FAILED)
            self.metrics.error_counts['pipeline_critical'] = 1
            self._save_pipeline_report()
            raise
    
    async def run_incremental_update(self) -> Dict[str, Any]:
        """
        Run incremental update for current year data.
        
        Returns:
            Pipeline execution results
        """
        current_year = datetime.now().year
        logger.info(f"Running incremental update for year {current_year}")
        
        return await self.run_pipeline(
            year=current_year,
            data_types=['announcements', 'contracts', 'modifications']
        )
    
    async def run_historical_import(
        self,
        start_year: int,
        end_year: int,
        data_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Run historical data import for a range of years.
        
        Args:
            start_year: Starting year
            end_year: Ending year
            data_types: Types of data to import
        
        Returns:
            List of pipeline results for each year
        """
        logger.info(f"Running historical import from {start_year} to {end_year}")
        
        results = []
        for year in range(start_year, end_year + 1):
            logger.info(f"Processing year {year}")
            try:
                result = await self.run_pipeline(year=year, data_types=data_types)
                results.append(result)
                
                # Add delay between years to be respectful to the API
                if year < end_year:
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Failed to process year {year}: {e}")
                results.append({
                    'year': year,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def _load_cached_data(
        self,
        year: int,
        data_types: List[str]
    ) -> Optional[Dict[str, List[Dict]]]:
        """
        Load cached data from raw directory.
        
        Args:
            year: Year to load
            data_types: Types of data to load
        
        Returns:
            Cached data or None if not found
        """
        cached_data = {}
        
        for dtype in data_types:
            file_path = self.raw_dir / dtype / f"{dtype}_{year}.json"
            if file_path.exists():
                # Check if file is recent (less than 24 hours old)
                file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age < timedelta(hours=24):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            cached_data[dtype] = data
                        elif isinstance(data, dict) and 'items' in data:
                            cached_data[dtype] = data['items']
                        else:
                            cached_data[dtype] = []
                else:
                    logger.info(f"Cache for {dtype} is older than 24 hours, will fetch fresh data")
                    return None
            else:
                logger.info(f"No cache found for {dtype}, will fetch fresh data")
                return None
        
        return cached_data if cached_data else None
    
    def _load_raw_data(
        self,
        year: int,
        data_types: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Load raw data from files.
        
        Args:
            year: Year to load
            data_types: Types of data to load
        
        Returns:
            Raw data dictionary
        """
        if data_types is None:
            data_types = ['announcements', 'contracts', 'modifications']
        
        raw_data = {}
        
        for dtype in data_types:
            file_path = self.raw_dir / dtype / f"{dtype}_{year}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        raw_data[dtype] = data
                    elif isinstance(data, dict) and 'items' in data:
                        raw_data[dtype] = data['items']
                    else:
                        raw_data[dtype] = []
                logger.info(f"Loaded {len(raw_data[dtype])} {dtype} from file")
            else:
                raw_data[dtype] = []
                logger.warning(f"No raw data file found for {dtype} year {year}")
        
        return raw_data
    
    def _save_invalid_records(self, invalid_records: List[Dict], data_type: str):
        """
        Save invalid records for review.
        
        Args:
            invalid_records: List of invalid record dictionaries
            data_type: Type of data
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = self.error_dir / f"invalid_{data_type}_{timestamp}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_records, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Saved {len(invalid_records)} invalid {data_type} records to {file_path}")
    
    def _save_pipeline_report(self):
        """Save pipeline execution report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.data_dir / 'reports'
        report_path.mkdir(exist_ok=True)
        
        file_path = report_path / f"pipeline_report_{timestamp}.json"
        
        report = self.metrics.to_dict()
        report['timestamp'] = timestamp
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Saved pipeline report to {file_path}")


async def main():
    """
    Example usage of the ETL Orchestrator.
    """
    # Initialize orchestrator
    orchestrator = ETLOrchestrator()
    
    # Run pipeline for current year
    results = await orchestrator.run_incremental_update()
    
    # Print results
    print("\nPipeline Results:")
    print(f"Status: {results['status']}")
    print(f"Duration: {results['duration_seconds']:.2f} seconds" if results['duration_seconds'] else "Duration: N/A")
    print(f"Total fetched: {results['total_fetched']}")
    print(f"Total validated: {results['total_validated']}")
    print(f"Total processed: {results['total_processed']}")
    print(f"Total errors: {results['total_errors']}")
    
    if results['errors']:
        print("\nErrors encountered:")
        for error_type, count in results['errors'].items():
            print(f"  {error_type}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
