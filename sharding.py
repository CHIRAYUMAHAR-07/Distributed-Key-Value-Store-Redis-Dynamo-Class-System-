"""
Consistent Hashing Implementation with Virtual Nodes
"""
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from bisect import bisect, bisect_left
from dataclasses import dataclass
import asyncio

@dataclass
class Node:
    id: str
    host: str
    port: int
    is_alive: bool = True
    virtual_nodes: int = 100  # Number of virtual nodes per physical node

class ConsistentHash:
    """Consistent Hashing with Virtual Nodes"""
    
    def __init__(self, nodes: Optional[List[Node]] = None):
        self.ring: Dict[int, str] = {}  # hash -> node_id
        self.nodes: Dict[str, Node] = {}  # node_id -> Node
        self.sorted_keys: List[int] = []
        
        if nodes:
            for node in nodes:
                self.add_node(node)
    
    def _hash(self, key: str) -> int:
        """MD5 hash function"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def add_node(self, node: Node):
        """Add a node to the hash ring"""
        self.nodes[node.id] = node
        
        for i in range(node.virtual_nodes):
            virtual_key = f"{node.id}:{i}"
            hash_key = self._hash(virtual_key)
            self.ring[hash_key] = node.id
        
        self._update_sorted_keys()
    
    def remove_node(self, node_id: str):
        """Remove a node from the hash ring"""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        for i in range(node.virtual_nodes):
            virtual_key = f"{node_id}:{i}"
            hash_key = self._hash(virtual_key)
            self.ring.pop(hash_key, None)
        
        self.nodes.pop(node_id)
        self._update_sorted_keys()
    
    def _update_sorted_keys(self):
        """Update sorted list of hash keys"""
        self.sorted_keys = sorted(self.ring.keys())
    
    def get_node(self, key: str) -> Optional[Node]:
        """Get the node responsible for a key"""
        if not self.ring:
            return None
        
        hash_key = self._hash(key)
        
        # Find the first node with hash >= key's hash
        idx = bisect(self.sorted_keys, hash_key)
        if idx == len(self.sorted_keys):
            idx = 0
        
        node_id = self.ring[self.sorted_keys[idx]]
        return self.nodes.get(node_id)
    
    def get_replica_nodes(self, key: str, num_replicas: int = 3) -> List[Node]:
        """Get N replica nodes for a key (including primary)"""
        if not self.ring:
            return []
        
        hash_key = self._hash(key)
        idx = bisect(self.sorted_keys, hash_key)
        if idx == len(self.sorted_keys):
            idx = 0
        
        replicas = []
        visited = set()
        
        # Start from primary node and walk the ring
        for i in range(len(self.sorted_keys)):
            current_idx = (idx + i) % len(self.sorted_keys)
            node_id = self.ring[self.sorted_keys[current_idx]]
            
            if node_id not in visited and node_id in self.nodes:
                replicas.append(self.nodes[node_id])
                visited.add(node_id)
                
                if len(replicas) == num_replicas:
                    break
        
        return replicas
    
    def rebalance_data(self, new_node: Node, old_nodes: List[Node]) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Calculate data to move when adding a new node
        Returns: {node_id: [(key, value), ...]}
        """
        redistribution = {}
        
        # For each existing node, find keys that should move to new node
        for old_node in old_nodes:
            moved_keys = []
            # In real implementation, you'd iterate through old_node's keys
            # This is simplified - you'd need to track key locations
            redistribution[old_node.id] = moved_keys
        
        return redistribution