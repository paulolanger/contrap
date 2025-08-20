#!/usr/bin/env python3
"""
ETL Pipeline CLI
Command-line interface for running the Contrap ETL pipeline.
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path
import logging

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator import ETLOrchestrator
from src.api_client import APIConfig


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('etl_pipeline.log')
        ]
    )


async def run_incremental(args):
    """Run incremental update for current year."""
    print(f"Running incremental update for {datetime.now().year}...")
    
    orchestrator = ETLOrchestrator(
        enable_cache=not args.no_cache
    )
    
    results = await orchestrator.run_incremental_update()
    
    print_results(results)
    return 0 if results['status'] in ['completed', 'partial'] else 1


async def run_year(args):
    """Run pipeline for a specific year."""
    print(f"Running pipeline for year {args.year}...")
    
    data_types = None
    if args.data_types:
        data_types = args.data_types.split(',')
    
    orchestrator = ETLOrchestrator(
        enable_cache=not args.no_cache
    )
    
    results = await orchestrator.run_pipeline(
        year=args.year,
        data_types=data_types,
        skip_fetch=args.skip_fetch
    )
    
    print_results(results)
    return 0 if results['status'] in ['completed', 'partial'] else 1


async def run_historical(args):
    """Run historical import for a range of years."""
    print(f"Running historical import from {args.start_year} to {args.end_year}...")
    
    data_types = None
    if args.data_types:
        data_types = args.data_types.split(',')
    
    orchestrator = ETLOrchestrator(
        enable_cache=not args.no_cache
    )
    
    results = await orchestrator.run_historical_import(
        start_year=args.start_year,
        end_year=args.end_year,
        data_types=data_types
    )
    
    # Print summary
    successful = sum(1 for r in results if r.get('status') == 'completed')
    partial = sum(1 for r in results if r.get('status') == 'partial')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    
    print(f"\nHistorical Import Summary:")
    print(f"  Successful: {successful}")
    print(f"  Partial: {partial}")
    print(f"  Failed: {failed}")
    
    for result in results:
        if result.get('status') == 'failed':
            year = result.get('year', 'Unknown')
            error = result.get('error', 'Unknown error')
            print(f"  Year {year} failed: {error}")
    
    return 0 if failed == 0 else 1


async def test_connection(args):
    """Test API and database connections."""
    print("Testing connections...")
    
    # Test API connection
    print("\nTesting API connection...")
    from src.api_client import ContrapAPIClient
    
    api_config = APIConfig()
    try:
        async with ContrapAPIClient(api_config) as client:
            # Try to fetch a small amount of data
            result = await client.get_announcements(2024)
            if result:
                print(f"✓ API connection successful. Found {len(result)} announcements for 2024.")
            else:
                print("✓ API connection successful but no data returned.")
    except Exception as e:
        print(f"✗ API connection failed: {e}")
        return 1
    
    # Test database connection
    print("\nTesting database connection...")
    from src.processor import DataProcessor
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'contrap'),
        'user': os.getenv('DB_USER', 'contrap'),
        'password': os.getenv('DB_PASSWORD', 'contrap')
    }
    
    try:
        processor = DataProcessor(db_config)
        async with processor:
            stats = await processor.get_statistics()
            print(f"✓ Database connection successful.")
            print(f"  Total entities: {stats.get('total_entities', 0)}")
            print(f"  Total announcements: {stats.get('total_announcements', 0)}")
            print(f"  Total contracts: {stats.get('total_contracts', 0)}")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return 1
    
    print("\n✓ All connections successful!")
    return 0


def print_results(results):
    """Print pipeline results."""
    print("\n" + "="*50)
    print("Pipeline Results")
    print("="*50)
    
    print(f"Status: {results['status']}")
    
    if results['duration_seconds']:
        duration = results['duration_seconds']
        if duration < 60:
            print(f"Duration: {duration:.2f} seconds")
        else:
            minutes = int(duration // 60)
            seconds = duration % 60
            print(f"Duration: {minutes}m {seconds:.0f}s")
    
    print(f"\nData Fetched:")
    print(f"  Total: {results['total_fetched']}")
    for dtype, count in results.get('fetched', {}).items():
        print(f"  - {dtype}: {count}")
    
    print(f"\nData Validated:")
    print(f"  Total: {results['total_validated']}")
    for dtype, count in results.get('validated', {}).items():
        print(f"  - {dtype}: {count}")
    
    print(f"\nData Processed:")
    print(f"  Total: {results['total_processed']}")
    for dtype, count in results.get('processed', {}).items():
        if dtype != 'errors':
            print(f"  - {dtype}: {count}")
    
    if results['total_errors'] > 0:
        print(f"\nErrors: {results['total_errors']}")
        for error_type, count in results.get('errors', {}).items():
            print(f"  - {error_type}: {count}")
    
    print("="*50)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Contrap ETL Pipeline CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run incremental update for current year
  python run_etl.py incremental
  
  # Run pipeline for specific year
  python run_etl.py year 2023
  
  # Run historical import
  python run_etl.py historical 2020 2023
  
  # Test connections
  python run_etl.py test
  
  # Run with specific data types
  python run_etl.py year 2024 --data-types announcements,contracts
  
  # Run without cache
  python run_etl.py incremental --no-cache
        """
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable cache and force fresh data fetch'
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Command to run'
    )
    
    # Incremental update command
    parser_incremental = subparsers.add_parser(
        'incremental',
        help='Run incremental update for current year'
    )
    parser_incremental.set_defaults(func=run_incremental)
    
    # Year command
    parser_year = subparsers.add_parser(
        'year',
        help='Run pipeline for a specific year'
    )
    parser_year.add_argument(
        'year',
        type=int,
        help='Year to process'
    )
    parser_year.add_argument(
        '--data-types',
        help='Comma-separated list of data types (announcements,contracts,modifications)'
    )
    parser_year.add_argument(
        '--skip-fetch',
        action='store_true',
        help='Skip fetching and use existing raw data'
    )
    parser_year.set_defaults(func=run_year)
    
    # Historical import command
    parser_historical = subparsers.add_parser(
        'historical',
        help='Run historical import for a range of years'
    )
    parser_historical.add_argument(
        'start_year',
        type=int,
        help='Starting year (inclusive)'
    )
    parser_historical.add_argument(
        'end_year',
        type=int,
        help='Ending year (inclusive)'
    )
    parser_historical.add_argument(
        '--data-types',
        help='Comma-separated list of data types (announcements,contracts,modifications)'
    )
    parser_historical.set_defaults(func=run_historical)
    
    # Test command
    parser_test = subparsers.add_parser(
        'test',
        help='Test API and database connections'
    )
    parser_test.set_defaults(func=test_connection)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Run the command
    try:
        return asyncio.run(args.func(args))
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
