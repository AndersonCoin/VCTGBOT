"""
Storage abstraction layer for different backends (memory, TinyDB, SQLite).
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any) -> bool:
        """Set value by key."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """Get all keys matching pattern."""
        pass


class MemoryStorage(StorageBackend):
    """In-memory storage backend."""
    
    def __init__(self):
        """Initialize memory storage."""
        self.data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        async with self._lock:
            return self.data.get(key)
    
    async def set(self, key: str, value: Any) -> bool:
        """Set value by key."""
        async with self._lock:
            self.data[key] = value
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        async with self._lock:
            if key in self.data:
                del self.data[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        async with self._lock:
            return key in self.data
    
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """Get all keys matching pattern."""
        async with self._lock:
            result = {}
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                for k, v in self.data.items():
                    if k.startswith(prefix):
                        result[k] = v
            else:
                # Exact match
                if pattern in self.data:
                    result[pattern] = self.data[pattern]
            return result


class TinyDBStorage(StorageBackend):
    """TinyDB storage backend."""
    
    def __init__(self, db_path: Path):
        """Initialize TinyDB storage."""
        self.db_path = db_path
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def _ensure_initialized(self):
        """Ensure TinyDB is initialized."""
        if not self._initialized:
            try:
                from tinydb import TinyDB
                from tinydb.storages import JSONStorage
                
                # Ensure directory exists
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.db = TinyDB(
                    self.db_path,
                    storage=JSONStorage,
                    indent=2
                )
                self._initialized = True
                
            except ImportError:
                logger.error("TinyDB not available, falling back to memory storage")
                raise ImportError("TinyDB not installed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        try:
            await self._ensure_initialized()
            async with self._lock:
                doc = self.db.get(doc_id=key)
                return doc.get('value') if doc else None
        except Exception as e:
            logger.error(f"TinyDB get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any) -> bool:
        """Set value by key."""
        try:
            await self._ensure_initialized()
            async with self._lock:
                doc = self.db.get(doc_id=key)
                if doc:
                    doc['value'] = value
                    self.db.update(doc, doc_ids=[key])
                else:
                    self.db.insert({'_id': key, 'value': value})
                return True
        except Exception as e:
            logger.error(f"TinyDB set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            await self._ensure_initialized()
            async with self._lock:
                doc = self.db.get(doc_id=key)
                if doc:
                    self.db.remove(doc_ids=[key])
                    return True
                return False
        except Exception as e:
            logger.error(f"TinyDB delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            await self._ensure_initialized()
            async with self._lock:
                doc = self.db.get(doc_id=key)
                return doc is not None
        except Exception as e:
            logger.error(f"TinyDB exists error for key {key}: {e}")
            return False
    
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """Get all keys matching pattern."""
        try:
            await self._ensure_initialized()
            async with self._lock:
                result = {}
                docs = self.db.all()
                
                for doc in docs:
                    key = doc.get('_id')
                    value = doc.get('value')
                    
                    if pattern.endswith('*'):
                        prefix = pattern[:-1]
                        if key and key.startswith(prefix):
                            result[key] = value
                    else:
                        if key == pattern:
                            result[key] = value
                            break
                
                return result
        except Exception as e:
            logger.error(f"TinyDB pattern error for pattern {pattern}: {e}")
            return {}


class SQLiteStorage(StorageBackend):
    """SQLite storage backend."""
    
    def __init__(self, db_path: Path):
        """Initialize SQLite storage."""
        self.db_path = db_path
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def _ensure_initialized(self):
        """Ensure SQLite is initialized."""
        if not self._initialized:
            try:
                import aiosqlite
                
                # Ensure directory exists
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute('''
                        CREATE TABLE IF NOT EXISTS key_value (
                            key TEXT PRIMARY KEY,
                            value TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    await db.commit()
                
                self._initialized = True
                
            except ImportError:
                logger.error("aiosqlite not available, falling back to memory storage")
                raise ImportError("aiosqlite not installed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        try:
            await self._ensure_initialized()
            import aiosqlite
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT value FROM key_value WHERE key = ?', 
                    (key,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row['value'])
                return None
                
        except Exception as e:
            logger.error(f"SQLite get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any) -> bool:
        """Set value by key."""
        try:
            await self._ensure_initialized()
            import aiosqlite
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                value_str = json.dumps(value)
                await db.execute(
                    '''
                    INSERT OR REPLACE INTO key_value (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''',
                    (key, value_str)
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"SQLite set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            await self._ensure_initialized()
            import aiosqlite
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'DELETE FROM key_value WHERE key = ?', 
                    (key,)
                )
                await db.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"SQLite delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            await self._ensure_initialized()
            import aiosqlite
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT 1 FROM key_value WHERE key = ?', 
                    (key,)
                )
                row = await cursor.fetchone()
                return row is not None
                
        except Exception as e:
            logger.error(f"SQLite exists error for key {key}: {e}")
            return False
    
    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """Get all keys matching pattern."""
        try:
            await self._ensure_initialized()
            import aiosqlite
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if pattern.endswith('*'):
                    prefix = pattern[:-1]
                    cursor = await db.execute(
                        'SELECT key, value FROM key_value WHERE key LIKE ?',
                        (f'{prefix}%',)
                    )
                else:
                    cursor = await db.execute(
                        'SELECT key, value FROM key_value WHERE key = ?',
                        (pattern,)
                    )
                
                rows = await cursor.fetchall()
                result = {}
                
                for row in rows:
                    try:
                        value = json.loads(row['value'])
                        result[row['key']] = value
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON for key {row['key']}")
                
                return result
                
        except Exception as e:
            logger.error(f"SQLite pattern error for pattern {pattern}: {e}")
            return {}


def create_storage_backend(backend_type: str, db_path: Path) -> StorageBackend:
    """Create storage backend based on type."""
    backend_type = backend_type.lower()
    
    if backend_type == "memory":
        return MemoryStorage()
    elif backend_type == "tinydb":
        return TinyDBStorage(db_path)
    elif backend_type == "sqlite":
        return SQLiteStorage(db_path)
    else:
        logger.warning(f"Unknown backend type '{backend_type}', using memory storage")
        return MemoryStorage()
