"""
Database adapter that can switch between mock and real PostgreSQL database
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date, time

logger = logging.getLogger(__name__)

# Always use real PostgreSQL database
try:
    from database_postgres import db
    logger.info("Using PostgreSQL database")
except ImportError as e:
    logger.error(f"Failed to import PostgreSQL database: {e}")
    raise ImportError("PostgreSQL database is required but could not be imported")

# Export the database instance
__all__ = ['db']
