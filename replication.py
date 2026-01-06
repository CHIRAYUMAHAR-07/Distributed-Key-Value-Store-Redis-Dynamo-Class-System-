"""
Raft Consensus Algorithm Implementation for Replication
"""
import asyncio
import random
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pickle

class Role(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

@dataclass
class LogEntry:
    term: int
    index: int
    command: Any
    key: str
    value: Optional[Any] = None

class RaftNode:
    """Raft consensus implementation"""
    
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers
        
        # Persistent state
        self.current_term = 0
        self.voted_for = None  # candidateId that received vote
        self.log: List[LogEntry] = []
        
        # Volatile state
        self.commit_index = 0
        self.last_applied = 0
        
        # Volatile state for leaders
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        
        # Node state
        self.role = Role.FOLLOWER
        self.leader_id = None
        self.votes_received = 0
        
        # Election timeout
        self.election_timeout = random.uniform(1.5, 3.0)
        self.last_heartbeat = time.time()
        
        # Append entries RPC
        self.append_entries_rpc = {}
        
        # Request vote RPC
        self.request_vote_rpc = {}
        
        # Start background tasks
        self._start_election_timer()
        self._start_heartbeat()
    
    def _start_election_timer(self):
        """Start election timeout timer"""
        async def timer():
            while True:
                await asyncio.sleep(0.1)
                if self.role == Role.FOLLOWER or self.role == Role.CANDIDATE:
                    if time.time() - self.last_heartbeat > self.election_timeout:
                        await self._start_election()
        
        asyncio.create_task(timer())
    
    def _start_heartbeat(self):
        """Start heartbeat timer for leader"""
        async def heartbeat():
            while True:
                await asyncio.sleep(0.05)
                if self.role == Role.LEADER:
                    await self._send_heartbeat()
        
        asyncio.create_task(heartbeat())
    
    async def _start_election(self):
        """Start a new election"""
        print(f"Node {self.node_id}: Starting election for term {self.current_term + 1}")
        
        self.role = Role.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = 1  # Vote for self
        
        # Reset election timeout
        self.election_timeout = random.uniform(1.5, 3.0)
        self.last_heartbeat = time.time()
        
        # Request votes from all peers
        for peer in self.peers:
            await self._request_vote(peer)
    
    async def _request_vote(self, peer_id: str):
        """Send RequestVote RPC to peer"""
        last_log_index = len(self.log) - 1
        last_log_term = self.log[-1].term if self.log else 0
        
        # In real implementation, send RPC to peer
        # This is simplified for demonstration
        print(f"Node {self.node_id}: Requesting vote from {peer_id}")
    
    async def _send_heartbeat(self):
        """Send heartbeat to all followers"""
        for peer in self.peers:
            await self._append_entries(peer, entries=[])
    
    async def _append_entries(self, peer_id: str, entries: List[LogEntry]):
        """Send AppendEntries RPC to follower"""
        # In real implementation, send log entries to replicate
        pass
    
    async def handle_append_entries(self, 
                                  term: int, 
                                  leader_id: str,
                                  prev_log_index: int,
                                  prev_log_term: int,
                                  entries: List[LogEntry],
                                  leader_commit: int) -> Tuple[bool, int]:
        """Handle incoming AppendEntries RPC"""
        # 1. Reply false if term < currentTerm
        if term < self.current_term:
            return False, self.current_term
        
        # Reset election timeout
        self.last_heartbeat = time.time()
        
        # If RPC term > current term, update term and convert to follower
        if term > self.current_term:
            self.current_term = term
            self.role = Role.FOLLOWER
            self.voted_for = None
        
        # Update leader
        self.leader_id = leader_id
        self.role = Role.FOLLOWER
        
        # 2. Reply false if log doesn't contain entry at prev_log_index
        if prev_log_index > 0:
            if len(self.log) < prev_log_index:
                return False, self.current_term
            if self.log[prev_log_index - 1].term != prev_log_term:
                return False, self.current_term
        
        # 3. If an existing entry conflicts with new one, delete it
        if entries:
            for i, entry in enumerate(entries):
                log_index = prev_log_index + i + 1
                if log_index <= len(self.log):
                    if self.log[log_index - 1].term != entry.term:
                        # Delete conflicting entry and all that follow
                        self.log = self.log[:log_index - 1]
        
        # 4. Append new entries not already in log
        for entry in entries:
            if entry.index > len(self.log):
                self.log.append(entry)
        
        # 5. If leaderCommit > commitIndex, update commitIndex
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))
        
        return True, self.current_term
    
    async def handle_request_vote(self,
                                term: int,
                                candidate_id: str,
                                last_log_index: int,
                                last_log_term: int) -> Tuple[bool, int]:
        """Handle RequestVote RPC"""
        # 1. Reply false if term < currentTerm
        if term < self.current_term:
            return False, self.current_term
        
        # If RPC term > current term, update term and convert to follower
        if term > self.current_term:
            self.current_term = term
            self.role = Role.FOLLOWER
            self.voted_for = None
        
        # 2. If votedFor is null or candidateId, and candidate's log is at least as up-to-date
        log_ok = (last_log_term > self.log[-1].term if self.log else 0) or \
                 (last_log_term == (self.log[-1].term if self.log else 0) and 
                  last_log_index >= len(self.log))
        
        if (self.voted_for is None or self.voted_for == candidate_id) and log_ok:
            self.voted_for = candidate_id
            # Reset election timeout
            self.last_heartbeat = time.time()
            return True, self.current_term
        
        return False, self.current_term
    
    async def replicate_operation(self, operation: str, key: str, value: Any = None) -> bool:
        """Replicate an operation through Raft"""
        if self.role != Role.LEADER:
            # Forward to leader
            return False
        
        # Create log entry
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log) + 1,
            command=operation,
            key=key,
            value=value
        )
        
        self.log.append(entry)
        
        # Replicate to followers
        success_count = 1  # Count self
        
        for peer in self.peers:
            # Send entry to follower
            # In real implementation, use actual RPC
            pass
        
        # Wait for majority
        if success_count >= (len(self.peers) + 1) // 2 + 1:
            self.commit_index = entry.index
            return True
        
        return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current Raft state"""
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "current_term": self.current_term,
            "leader_id": self.leader_id,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "peers": self.peers
        }

class ReplicationManager:
    """Manages replication across nodes"""
    
    def __init__(self, node_id: str, shard_id: str, replica_nodes: List[str]):
        self.node_id = node_id
        self.shard_id = shard_id
        self.replica_nodes = replica_nodes
        
        # Raft consensus
        self.raft = RaftNode(node_id, replica_nodes)
        
        # Replication state
        self.is_leader = False
        self.followers: Dict[str, bool] = {}  # follower_id -> is_alive
        
        # Sync queue
        self.pending_sync = asyncio.Queue()
        
        # Start replication worker
        self._start_replication_worker()
    
    def _start_replication_worker(self):
        """Start background replication worker"""
        async def worker():
            while True:
                try:
                    operation, key, value, ttl = await self.pending_sync.get()
                    await self._replicate_to_followers(operation, key, value, ttl)
                except Exception as e:
                    print(f"Replication error: {e}")
        
        asyncio.create_task(worker())
    
    async def _replicate_to_followers(self, operation: str, key: str, value: Any, ttl: Optional[int]):
        """Replicate operation to all followers"""
        if not self.is_leader:
            return
        
        # Use Raft for consensus
        success = await self.raft.replicate_operation(operation, key, value)
        
        if success:
            # Apply to local storage
            # This would call the storage engine
            pass
        
        # Also replicate asynchronously for performance
        tasks = []
        for follower in self.replica_nodes:
            if follower != self.node_id:
                task = self._send_to_follower(follower, operation, key, value, ttl)
                tasks.append(task)
        
        # Wait for majority
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if r is True)
            return successful >= len(self.replica_nodes) // 2
        
        return True
    
    async def _send_to_follower(self, follower_id: str, operation: str, key: str, 
                              value: Any, ttl: Optional[int]) -> bool:
        """Send operation to a specific follower"""
        # In real implementation, make HTTP/gRPC call to follower
        try:
            # Simulate network call
            await asyncio.sleep(0.01)
            
            # Randomly simulate failures (for testing)
            if random.random() < 0.05:  # 5% failure rate
                return False
            
            return True
        except:
            return False
    
    async def handle_follower_request(self, operation: str, key: str, 
                                    value: Any = None, ttl: Optional[int] = None) -> bool:
        """Handle replication request from leader"""
        if self.is_leader:
            return False
        
        # Apply operation to local storage
        # This would call the storage engine
        print(f"Follower {self.node_id}: Applying {operation} for key {key}")
        return True
    
    def promote_to_leader(self):
        """Promote this node to leader"""
        self.is_leader = True
        self.raft.role = Role.LEADER
        print(f"Node {self.node_id} promoted to leader for shard {self.shard_id}")
    
    def demote_to_follower(self):
        """Demote this node to follower"""
        self.is_leader = False
        self.raft.role = Role.FOLLOWER
    
    def get_replication_status(self) -> Dict[str, Any]:
        """Get replication status"""
        raft_state = self.raft.get_state()
        
        return {
            **raft_state,
            "shard_id": self.shard_id,
            "is_leader": self.is_leader,
            "followers": list(self.followers.keys()),
            "alive_followers": sum(1 for alive in self.followers.values() if alive),
            "total_followers": len(self.followers)
        }