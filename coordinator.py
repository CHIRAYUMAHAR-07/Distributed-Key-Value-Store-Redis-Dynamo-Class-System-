"""
Coordinator/Proxy Server for Request Routing
"""
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from .sharding import ConsistentHash, Node
from .protocol import KVRequest, KVResponse, Operation, ConsistencyLevel
from .heartbeat import HeartbeatManager

@dataclass
class ClusterConfig:
    """Cluster configuration"""
    replication_factor: int = 3
    write_quorum: int = 2
    read_quorum: int = 2
    consistency_level: ConsistencyLevel = ConsistencyLevel.QUORUM

class Coordinator:
    """Main coordinator for request routing"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 8080,
                 cluster_config: Optional[ClusterConfig] = None):
        self.host = host
        self.port = port
        self.config = cluster_config or ClusterConfig()
        
        # Hash ring for sharding
        self.hash_ring = ConsistentHash()
        
        # Node registry
        self.nodes: Dict[str, Node] = {}
        
        # Heartbeat manager for failure detection
        self.heartbeat_manager = HeartbeatManager(self)
        
        # Request cache for idempotency
        self.request_cache: Dict[str, KVResponse] = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency": 0.0,
            "nodes_online": 0
        }
        
        # FastAPI app
        self.app = FastAPI(title="KVStore Coordinator")
        self._setup_routes()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _setup_routes(self):
        """Setup HTTP API routes"""
        
        @self.app.get("/")
        async def root():
            return {"status": "online", "service": "kvstore-coordinator"}
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": time.time()}
        
        @self.app.get("/get/{key}")
        async def get_key(key: str, 
                         consistency: ConsistencyLevel = ConsistencyLevel.QUORUM):
            """Get a key"""
            return await self.handle_get(key, consistency)
        
        @self.app.post("/set/{key}")
        async def set_key(key: str, 
                         value: Any, 
                         ttl: Optional[int] = None,
                         background_tasks: BackgroundTasks = None):
            """Set a key-value pair"""
            return await self.handle_put(key, value, ttl)
        
        @self.app.delete("/delete/{key}")
        async def delete_key(key: str):
            """Delete a key"""
            return await self.handle_delete(key)
        
        @self.app.get("/cluster/status")
        async def cluster_status():
            """Get cluster status"""
            return self.get_cluster_status()
        
        @self.app.post("/cluster/node")
        async def add_node(node_info: dict):
            """Add a node to cluster"""
            node = Node(
                id=node_info["id"],
                host=node_info["host"],
                port=node_info["port"]
            )
            self.add_node(node)
            return {"success": True, "node_id": node.id}
        
        @self.app.delete("/cluster/node/{node_id}")
        async def remove_node(node_id: str):
            """Remove a node from cluster"""
            self.remove_node(node_id)
            return {"success": True, "node_id": node_id}
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        async def cleanup_cache():
            while True:
                await asyncio.sleep(60)  # Clean cache every minute
                self._clean_request_cache()
        
        asyncio.create_task(cleanup_cache())
    
    def _clean_request_cache(self):
        """Clean old entries from request cache"""
        current_time = time.time()
        to_remove = []
        
        for request_id, response in self.request_cache.items():
            if current_time - response.timestamp > 300:  # 5 minutes
                to_remove.append(request_id)
        
        for request_id in to_remove:
            self.request_cache.pop(request_id, None)
    
    def add_node(self, node: Node):
        """Add a node to the cluster"""
        self.nodes[node.id] = node
        self.hash_ring.add_node(node)
        self.heartbeat_manager.add_node(node.id, node.host, node.port)
        
        print(f"Added node {node.id} at {node.host}:{node.port}")
        self.stats["nodes_online"] += 1
    
    def remove_node(self, node_id: str):
        """Remove a node from the cluster"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            self.hash_ring.remove_node(node_id)
            self.heartbeat_manager.remove_node(node_id)
            self.nodes.pop(node_id)
            
            print(f"Removed node {node_id}")
            self.stats["nodes_online"] -= 1
    
    async def handle_get(self, key: str, consistency: ConsistencyLevel) -> Dict[str, Any]:
        """Handle GET request"""
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            # Get replica nodes
            replica_nodes = self.hash_ring.get_replica_nodes(
                key, 
                self.config.replication_factor
            )
            
            if not replica_nodes:
                self.stats["failed_requests"] += 1
                raise HTTPException(status_code=503, detail="No nodes available")
            
            # Determine how many nodes to read from
            if consistency == ConsistencyLevel.STRONG:
                # Read from leader
                leader_node = replica_nodes[0]  # First node is leader
                value = await self._read_from_node(leader_node, key)
                response = {"success": True, "value": value}
                
            elif consistency == ConsistencyLevel.QUORUM:
                # Read from quorum
                quorum_size = (len(replica_nodes) // 2) + 1
                values = await asyncio.gather(
                    *[self._read_from_node(node, key) for node in replica_nodes[:quorum_size]]
                )
                # Get most recent value (in real impl, check timestamps/versions)
                value = next((v for v in values if v is not None), None)
                response = {"success": True, "value": value}
                
            else:  # EVENTUAL
                # Read from any node
                for node in replica_nodes:
                    value = await self._read_from_node(node, key)
                    if value is not None:
                        response = {"success": True, "value": value}
                        break
                else:
                    response = {"success": False, "error": "Key not found"}
            
            latency = time.time() - start_time
            self.stats["avg_latency"] = (
                (self.stats["avg_latency"] * (self.stats["total_requests"] - 1) + latency) 
                / self.stats["total_requests"]
            )
            
            if response["success"]:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
            
            return response
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_put(self, key: str, value: Any, ttl: Optional[int]) -> Dict[str, Any]:
        """Handle PUT request"""
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            # Get replica nodes
            replica_nodes = self.hash_ring.get_replica_nodes(
                key, 
                self.config.replication_factor
            )
            
            if not replica_nodes:
                self.stats["failed_requests"] += 1
                raise HTTPException(status_code=503, detail="No nodes available")
            
            # Write to multiple nodes based on quorum
            write_quorum = min(self.config.write_quorum, len(replica_nodes))
            
            tasks = []
            for node in replica_nodes[:write_quorum]:
                task = self._write_to_node(node, key, value, ttl)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_writes = sum(1 for r in results if r is True)
            
            if successful_writes >= write_quorum:
                latency = time.time() - start_time
                self.stats["avg_latency"] = (
                    (self.stats["avg_latency"] * (self.stats["total_requests"] - 1) + latency) 
                    / self.stats["total_requests"]
                )
                self.stats["successful_requests"] += 1
                
                # Asynchronously replicate to remaining nodes
                remaining_nodes = replica_nodes[write_quorum:]
                if remaining_nodes:
                    asyncio.create_task(
                        self._async_replicate(remaining_nodes, key, value, ttl)
                    )
                
                return {"success": True, "writes": successful_writes}
            else:
                self.stats["failed_requests"] += 1
                raise HTTPException(
                    status_code=500, 
                    detail=f"Write failed. Only {successful_writes}/{write_quorum} successful"
                )
                
        except Exception as e:
            self.stats["failed_requests"] += 1
            raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_delete(self, key: str) -> Dict[str, Any]:
        """Handle DELETE request"""
        # Similar to PUT but with delete operation
        return await self.handle_put(key, None, None)  # Value None indicates delete
    
    async def _read_from_node(self, node: Node, key: str) -> Any:
        """Read from a specific node"""
        url = f"http://{node.host}:{node.port}/get/{key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("value")
                    else:
                        return None
        except:
            # Mark node as potentially dead
            self.heartbeat_manager.report_failure(node.id)
            return None
    
    async def _write_to_node(self, node: Node, key: str, value: Any, ttl: Optional[int]) -> bool:
        """Write to a specific node"""
        url = f"http://{node.host}:{node.port}/set/{key}"
        
        try:
            payload = {"value": value}
            if ttl:
                payload["ttl"] = ttl
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as response:
                    return response.status == 200
        except:
            # Mark node as potentially dead
            self.heartbeat_manager.report_failure(node.id)
            return False
    
    async def _async_replicate(self, nodes: List[Node], key: str, value: Any, ttl: Optional[int]):
        """Asynchronously replicate to additional nodes"""
        for node in nodes:
            try:
                await self._write_to_node(node, key, value, ttl)
            except:
                pass  # Ignore failures in async replication
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get complete cluster status"""
        node_statuses = []
        
        for node_id, node in self.nodes.items():
            node_statuses.append({
                "id": node_id,
                "host": node.host,
                "port": node.port,
                "is_alive": node.is_alive,
                "virtual_nodes": node.virtual_nodes
            })
        
        return {
            "coordinator": f"{self.host}:{self.port}",
            "total_nodes": len(self.nodes),
            "alive_nodes": self.stats["nodes_online"],
            "nodes": node_statuses,
            "config": {
                "replication_factor": self.config.replication_factor,
                "write_quorum": self.config.write_quorum,
                "read_quorum": self.config.read_quorum
            },
            "stats": self.stats
        }
    
    def run(self):
        """Run the coordinator server"""
        uvicorn.run(self.app, host=self.host, port=self.port)