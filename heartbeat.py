"""
Heartbeat and Failure Detection System
"""
import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import aiohttp

@dataclass
class NodeStatus:
    node_id: str
    host: str
    port: int
    is_alive: bool = True
    last_heartbeat: float = 0
    failure_count: int = 0
    response_time: float = 0

class HeartbeatManager:
    """Manages node health checking and failure detection"""
    
    def __init__(self, coordinator, check_interval: float = 5.0, failure_threshold: int = 3):
        self.coordinator = coordinator
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        
        self.nodes: Dict[str, NodeStatus] = {}
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.on_node_failure: Optional[Callable] = None
        self.on_node_recovery: Optional[Callable] = None
    
    def add_node(self, node_id: str, host: str, port: int):
        """Add a node to heartbeat monitoring"""
        self.nodes[node_id] = NodeStatus(
            node_id=node_id,
            host=host,
            port=port,
            last_heartbeat=time.time(),
            is_alive=True
        )
    
    def remove_node(self, node_id: str):
        """Remove a node from monitoring"""
        self.nodes.pop(node_id, None)
    
    def report_failure(self, node_id: str):
        """Report a node failure"""
        if node_id in self.nodes:
            self.nodes[node_id].failure_count += 1
            
            if self.nodes[node_id].failure_count >= self.failure_threshold:
                self._mark_node_dead(node_id)
    
    def _mark_node_dead(self, node_id: str):
        """Mark a node as dead"""
        if node_id in self.nodes:
            print(f"Heartbeat: Marking node {node_id} as dead")
            self.nodes[node_id].is_alive = False
            
            # Update node in hash ring
            if node_id in self.coordinator.nodes:
                self.coordinator.nodes[node_id].is_alive = False
            
            # Trigger callback
            if self.on_node_failure:
                self.on_node_failure(node_id)
    
    def _mark_node_alive(self, node_id: str):
        """Mark a node as alive"""
        if node_id in self.nodes:
            print(f"Heartbeat: Node {node_id} recovered")
            self.nodes[node_id].is_alive = True
            self.nodes[node_id].failure_count = 0
            
            # Update node in hash ring
            if node_id in self.coordinator.nodes:
                self.coordinator.nodes[node_id].is_alive = True
            
            # Trigger callback
            if self.on_node_recovery:
                self.on_node_recovery(node_id)
    
    async def check_node(self, node_status: NodeStatus) -> bool:
        """Check if a node is alive"""
        try:
            start_time = time.time()
            url = f"http://{node_status.host}:{node_status.port}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=2) as response:
                    if response.status == 200:
                        node_status.response_time = time.time() - start_time
                        node_status.last_heartbeat = time.time()
                        return True
                    else:
                        return False
        except Exception as e:
            print(f"Heartbeat check failed for {node_status.node_id}: {e}")
            return False
    
    async def _worker(self):
        """Background worker for heartbeat checks"""
        while self.running:
            await asyncio.sleep(self.check_interval)
            
            tasks = []
            for node_status in self.nodes.values():
                tasks.append(self.check_node(node_status))
            
            # Check all nodes in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for node_status, result in zip(self.nodes.values(), results):
                if isinstance(result, Exception) or not result:
                    # Check failed
                    self.report_failure(node_status.node_id)
                else:
                    # Check succeeded
                    if not node_status.is_alive:
                        self._mark_node_alive(node_status.node_id)
                    else:
                        node_status.failure_count = max(0, node_status.failure_count - 1)
    
    def start(self):
        """Start heartbeat monitoring"""
        if not self.running:
            self.running = True
            self.worker_task = asyncio.create_task(self._worker())
            print("Heartbeat manager started")
    
    def stop(self):
        """Stop heartbeat monitoring"""
        if self.running:
            self.running = False
            if self.worker_task:
                self.worker_task.cancel()
            print("Heartbeat manager stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get heartbeat status"""
        alive_nodes = [n for n in self.nodes.values() if n.is_alive]
        dead_nodes = [n for n in self.nodes.values() if not n.is_alive]
        
        return {
            "total_nodes": len(self.nodes),
            "alive_nodes": len(alive_nodes),
            "dead_nodes": len(dead_nodes),
            "check_interval": self.check_interval,
            "failure_threshold": self.failure_threshold,
            "alive": [{"id": n.node_id, "response_time": n.response_time} for n in alive_nodes],
            "dead": [{"id": n.node_id, "failure_count": n.failure_count} for n in dead_nodes]
        }