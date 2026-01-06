"""
RPC Protocol Definitions
"""
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from enum import Enum
import msgpack
import hashlib
from datetime import datetime, timedelta

class Operation(Enum):
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"
    EXISTS = "EXISTS"
    SCAN = "SCAN"
    INCR = "INCR"
    DECR = "DECR"

class ConsistencyLevel(Enum):
    STRONG = "STRONG"      # Read from leader, synchronous replication
    EVENTUAL = "EVENTUAL"  # Read from any replica
    QUORUM = "QUORUM"      # Read from majority

@dataclass
class KVRequest:
    operation: Operation
    key: str
    value: Optional[Any] = None
    ttl: Optional[int] = None  # seconds
    consistency: ConsistencyLevel = ConsistencyLevel.STRONG
    client_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[float] = None
    
    def serialize(self) -> bytes:
        data = {
            'op': self.operation.value,
            'key': self.key,
            'value': self.value,
            'ttl': self.ttl,
            'consistency': self.consistency.value,
            'client_id': self.client_id,
            'request_id': self.request_id,
            'timestamp': self.timestamp or datetime.now().timestamp()
        }
        return msgpack.packb(data, use_bin_type=True)
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'KVRequest':
        decoded = msgpack.unpackb(data, raw=False)
        return cls(
            operation=Operation(decoded['op']),
            key=decoded['key'],
            value=decoded.get('value'),
            ttl=decoded.get('ttl'),
            consistency=ConsistencyLevel(decoded.get('consistency', 'STRONG')),
            client_id=decoded.get('client_id'),
            request_id=decoded.get('request_id'),
            timestamp=decoded.get('timestamp')
        )

@dataclass
class KVResponse:
    success: bool
    value: Optional[Any] = None
    error: Optional[str] = None
    node_id: Optional[str] = None
    timestamp: float = None
    
    def serialize(self) -> bytes:
        data = {
            'success': self.success,
            'value': self.value,
            'error': self.error,
            'node_id': self.node_id,
            'timestamp': self.timestamp or datetime.now().timestamp()
        }
        return msgpack.packb(data, use_bin_type=True)
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'KVResponse':
        decoded = msgpack.unpackb(data, raw=False)
        return cls(
            success=decoded['success'],
            value=decoded.get('value'),
            error=decoded.get('error'),
            node_id=decoded.get('node_id'),
            timestamp=decoded.get('timestamp')
        )