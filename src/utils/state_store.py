"""State persistence for bot conversations."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger("datapilot")


class StateStore:
    """Manages conversation state persistence."""
    
    def __init__(self, store_type: str = "sqlite", path: str = "./data/state.db"):
        """
        Initialize state store.
        
        Args:
            store_type: Type of store ("sqlite" or "redis")
            path: Path to SQLite database (for sqlite type)
        """
        self.store_type = store_type
        self.path = Path(path)
        
        if store_type == "sqlite":
            self._init_sqlite()
        elif store_type == "redis":
            # TODO: Implement Redis support
            raise NotImplementedError("Redis support not yet implemented")
        else:
            raise ValueError(f"Unknown store type: {store_type}")
    
    def _init_sqlite(self):
        """Initialize SQLite database."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL,
                context TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_states(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"State store initialized at {self.path}")
    
    def get_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's current state.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            State dict with 'state' and 'context' keys, or None if not found
        """
        conn = sqlite3.connect(str(self.path))
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT state, context FROM user_states WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "state": row[0],
                "context": json.loads(row[1]) if row[1] else {}
            }
        return None
    
    def set_state(self, user_id: int, state: str, context: Optional[Dict[str, Any]] = None):
        """
        Update user's state.
        
        Args:
            user_id: Telegram user ID
            state: New state name
            context: Optional context dictionary
        """
        conn = sqlite3.connect(str(self.path))
        cursor = conn.cursor()
        
        context_json = json.dumps(context or {})
        cursor.execute("""
            INSERT OR REPLACE INTO user_states (user_id, state, context, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, state, context_json, datetime.utcnow()))
        
        conn.commit()
        conn.close()
        logger.debug(f"State updated for user {user_id}: {state}")
    
    def add_message(self, user_id: int, message_type: str, content: str, 
                   metadata: Optional[Dict[str, Any]] = None):
        """
        Add a message to conversation history.
        
        Args:
            user_id: Telegram user ID
            message_type: 'user' or 'bot'
            content: Message content
            metadata: Optional metadata dictionary
        """
        conn = sqlite3.connect(str(self.path))
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata or {})
        cursor.execute("""
            INSERT INTO conversation_history (user_id, message_type, content, metadata)
            VALUES (?, ?, ?, ?)
        """, (user_id, message_type, content, metadata_json))
        
        conn.commit()
        conn.close()
    
    def get_recent_messages(self, user_id: int, limit: int = 5) -> list:
        """
        Get recent conversation messages.
        
        Args:
            user_id: Telegram user ID
            limit: Number of messages to retrieve
            
        Returns:
            List of message dicts
        """
        conn = sqlite3.connect(str(self.path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT message_type, content, metadata, created_at
            FROM conversation_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            messages.append({
                "type": row[0],
                "content": row[1],
                "metadata": json.loads(row[2]) if row[2] else {},
                "created_at": row[3]
            })
        
        return messages

