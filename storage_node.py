"""
Storage Node with LSM-Tree inspired storage engine
"""
import asyncio
import pickle
import json
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import aiosqlite
import msgpack
import zlib
from bloom_filter2 import BloomFilter

@dataclass
class StorageEntry:
    value: Any
    timestamp: float
    ttl: Optional[int] = None
    version: int = 1
    deleted: bool = False

class MemoryTable:
    """In-memory storage (memtable)"""
    
    def __init__(self, max_size: int = 1000):
        self.data: Dict[str, StorageEntry] = {}
        self.max_size = max_size
        self.bloom_filter = BloomFilter(max_elements=10000, error_rate=0.01)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> StorageEntry:
        entry = StorageEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            version=1
        )
        self.data[key] = entry
        self.bloom_filter.add(key)
        return entry
    
    def get(self, key: str) -> Optional[StorageEntry]:
        # Check bloom filter first (fast path)
        if key not in self.bloom_filter:
            return None
        return self.data.get(key)
    
    def delete(self, key: str) -> bool:
        if key in self.data:
            self.data[key].deleted = True
            return True
        return False
    
    def size(self) -> int:
        return len(self.data)
    
    def should_flush(self) -> bool:
        return self.size() >= self.max_size
    
    def clear(self):
        self.data.clear()

class SSTable:
    """Sorted String Table on disk"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.index: Dict[str, int] = {}  # key -> file position
        self.bloom_filter = BloomFilter(max_elements=10000, error_rate=0.01)
        self._load_index()
    
    def _load_index(self):
        """Load index from index file"""
        index_file = self.filepath.with_suffix('.idx')
        if index_file.exists():
            with open(index_file, 'rb') as f:
                self.index = pickle.load(f)
    
    def save(self, data: Dict[str, StorageEntry]):
        """Save data to SSTable"""
        sorted_keys = sorted(data.keys())
        
        with open(self.filepath, 'ab') as f:
            for key in sorted_keys:
                entry = data[key]
                if entry.deleted:
                    continue  # Skip deleted entries
                
                # Write entry
                position = f.tell()
                entry_data = {
                    'key': key,
                    'value': entry.value,
                    'timestamp': entry.timestamp,
                    'ttl': entry.ttl,
                    'version': entry.version
                }
                packed = msgpack.packb(entry_data, use_bin_type=True)
                compressed = zlib.compress(packed)
                
                # Write length then data
                f.write(len(compressed).to_bytes(4, 'big'))
                f.write(compressed)
                
                # Update index
                self.index[key] = position
                self.bloom_filter.add(key)
        
        # Save index
        with open(self.filepath.with_suffix('.idx'), 'wb') as f:
            pickle.dump(self.index, f)
    
    def get(self, key: str) -> Optional[StorageEntry]:
        """Get value from SSTable"""
        if key not in self.bloom_filter:
            return None
        
        position = self.index.get(key)
        if position is None:
            return None
        
        with open(self.filepath, 'rb') as f:
            f.seek(position)
            length_bytes = f.read(4)
            if len(length_bytes) != 4:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            compressed = f.read(length)
            packed = zlib.decompress(compressed)
            data = msgpack.unpackb(packed, raw=False)
            
            return StorageEntry(
                value=data['value'],
                timestamp=data['timestamp'],
                ttl=data.get('ttl'),
                version=data.get('version', 1)
            )

class StorageEngine:
    """LSM-Tree inspired storage engine"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.memtable = MemoryTable()
        self.sstables: List[SSTable] = []
        self.write_lock = threading.Lock()
        self.compaction_thread = None
        
        # Load existing SSTables
        self._load_sstables()
        
        # Start background compaction
        self._start_compaction()
    
    def _load_sstables(self):
        """Load existing SSTables from disk"""
        sstable_files = sorted(self.data_dir.glob("sstable_*.dat"))
        for file in sstable_files:
            self.sstables.append(SSTable(file))
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None):
        """Write key-value pair"""
        with self.write_lock:
            entry = self.memtable.put(key, value, ttl)
            
            # Flush memtable to SSTable if too large
            if self.memtable.should_flush():
                self._flush_memtable()
            
            return entry
    
    def get(self, key: str) -> Optional[Any]:
        """Read key-value pair"""
        # Check memtable first
        entry = self.memtable.get(key)
        if entry:
            if self._is_expired(entry):
                return None
            return entry.value
        
        # Check SSTables (newest to oldest)
        for sstable in reversed(self.sstables):
            entry = sstable.get(key)
            if entry:
                if self._is_expired(entry):
                    return None
                return entry.value
        
        return None
    
    def delete(self, key: str) -> bool:
        """Mark key as deleted (tombstone)"""
        with self.write_lock:
            return self.memtable.delete(key)
    
    def _is_expired(self, entry: StorageEntry) -> bool:
        """Check if entry has expired"""
        if entry.ttl is None:
            return False
        return time.time() > entry.timestamp + entry.ttl
    
    def _flush_memtable(self):
        """Flush memtable to SSTable"""
        if not self.memtable.data:
            return
        
        # Create new SSTable
        timestamp = int(time.time())
        sstable_file = self.data_dir / f"sstable_{timestamp}.dat"
        sstable = SSTable(sstable_file)
        sstable.save(self.memtable.data)
        
        self.sstables.append(sstable)
        self.memtable.clear()
    
    def _start_compaction(self):
        """Start background compaction thread"""
        def compact():
            while True:
                time.sleep(300)  # Compact every 5 minutes
                self._compact_sstables()
        
        self.compaction_thread = threading.Thread(target=compact, daemon=True)
        self.compaction_thread.start()
    
    def _compact_sstables(self):
        """Compact SSTables to remove deleted/duplicate entries"""
        if len(self.sstables) < 2:
            return
        
        # Merge SSTables (simplified)
        merged_data = {}
        for sstable in self.sstables:
            # In real implementation, you'd merge sorted data
            pass
        
        # Create new compacted SSTable
        timestamp = int(time.time())
        new_file = self.data_dir / f"compacted_{timestamp}.dat"
        new_sstable = SSTable(new_file)
        new_sstable.save(merged_data)
        
        # Replace old SSTables
        self.sstables = [new_sstable]

class StorageNode:
    """Complete storage node with HTTP API"""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8000):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.storage = StorageEngine(f"./data/{node_id}")
        self.is_leader = False
        self.followers: List[str] = []
        
        # Statistics
        self.stats = {
            "ops_count": 0,
            "hits": 0,
            "misses": 0,
            "storage_size": 0
        }
    
    async def handle_request(self, request_data: bytes) -> bytes:
        """Process incoming request"""
        from .protocol import KVRequest, KVResponse
        
        try:
            request = KVRequest.deserialize(request_data)
            self.stats["ops_count"] += 1
            
            if request.operation == Operation.GET:
                value = self.storage.get(request.key)
                if value is not None:
                    self.stats["hits"] += 1
                    return KVResponse(
                        success=True,
                        value=value,
                        node_id=self.node_id
                    ).serialize()
                else:
                    self.stats["misses"] += 1
                    return KVResponse(
                        success=False,
                        error="Key not found",
                        node_id=self.node_id
                    ).serialize()
            
            elif request.operation == Operation.PUT:
                self.storage.put(request.key, request.value, request.ttl)
                return KVResponse(
                    success=True,
                    node_id=self.node_id
                ).serialize()
            
            elif request.operation == Operation.DELETE:
                success = self.storage.delete(request.key)
                return KVResponse(
                    success=success,
                    node_id=self.node_id
                ).serialize()
            
            else:
                return KVResponse(
                    success=False,
                    error=f"Unsupported operation: {request.operation}",
                    node_id=self.node_id
                ).serialize()
                
        except Exception as e:
            return KVResponse(
                success=False,
                error=str(e),
                node_id=self.node_id
            ).serialize()