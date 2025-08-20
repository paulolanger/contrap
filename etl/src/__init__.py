"""
Contrap ETL Pipeline
====================

This module contains the ETL (Extract, Transform, Load) pipeline for the Contrap platform.
It fetches data from the Portuguese Government Procurement API, processes it, and loads it
into a PostgreSQL database.

Main components:
- api_client: Async API client with retry logic
- fetcher: Data fetching from government API
- validator: Data validation and cleaning
- processor: Data normalization and transformation
- loader: Database loading with upsert logic
- pipeline: Main ETL orchestration
"""

__version__ = "0.1.0"
__author__ = "Contrap Development Team"
