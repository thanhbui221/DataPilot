"""Database connection manager using LangChain SQLDatabase."""
from langchain_community.utilities import SQLDatabase
from typing import Optional
import logging

logger = logging.getLogger("datapilot")


class DatabaseManager:
    """Manages SQL database connections using LangChain SQLDatabase."""
    
    def __init__(self, db_uri: str, read_only: bool = True):
        """
        Initialize database manager.
        
        Args:
            db_uri: Database URI (e.g., "sqlite:///data/sample.db")
            read_only: If True, enforce read-only mode (application level)
        """
        self.db_uri = db_uri
        self.read_only = read_only
        self._db: Optional[SQLDatabase] = None
    
    def connect(self) -> SQLDatabase:
        """Get or create a SQLDatabase connection."""
        if self._db is None:
            logger.info(f"Connecting to database (read-only={self.read_only}): {self.db_uri}")
            self._db = SQLDatabase.from_uri(self.db_uri)
            tables = self._db.get_usable_table_names()
            logger.info(f"Connected. Available tables: {tables}")
        
        return self._db
    
    def get_db(self) -> SQLDatabase:
        """Get the SQLDatabase instance."""
        return self.connect()
    
    def close(self):
        """Close the database connection."""
        self._db = None
        logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
