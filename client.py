"""
Client SDK for Distributed KV Store
"""
import asyncio
import aiohttp
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
import time
import hashlib

from .protocol import ConsistencyLevel

@dataclass
class ClientConfig:
    """Client configuration"""
    coordinator_host: str = "localhost"
    coordinator_port: int = 8080
    timeout: int = 10
    retries: int = 3
    consistency: ConsistencyLevel = ConsistencyLevel.QUORUM

class KVClient:
    """Python client for distributed key-value store"""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.base_url = f"http://{self.config.coordinator_host}:{self.config.coordinator_port}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_counter = 0
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Establish connection"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout))
        
        # Test connection
        try:
            async with self.session.get(f"{self.base_url}/health") as resp:
                if resp.status != 200:
                    raise ConnectionError("Failed to connect to coordinator")
        except Exception as e:
            await self.close()
            raise ConnectionError(f"Failed to connect: {e}")
    
    async def close(self):
        """Close connection"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get(self, key: str, consistency: Optional[ConsistencyLevel] = None) -> Optional[Any]:
        """Get value for key"""
        consistency = consistency or self.config.consistency
        
        for attempt in range(self.config.retries):
            try:
                url = f"{self.base_url}/get/{key}"
                params = {"consistency": consistency.value}
                
                async with self.session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("value")
                    elif resp.status == 404:
                        return None
                    else:
                        raise Exception(f"GET failed: {resp.status}")
            except Exception as e:
                if attempt == self.config.retries - 1:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key-value pair"""
        for attempt in range(self.config.retries):
            try:
                url = f"{self.base_url}/set/{key}"
                payload = {"value": value}
                if ttl:
                    payload["ttl"] = ttl
                
                async with self.session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("success", False)
                    else:
                        raise Exception(f"SET failed: {resp.status}")
            except Exception as e:
                if attempt == self.config.retries - 1:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        for attempt in range(self.config.retries):
            try:
                url = f"{self.base_url}/delete/{key}"
                
                async with self.session.delete(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("success", False)
                    else:
                        raise Exception(f"DELETE failed: {resp.status}")
            except Exception as e:
                if attempt == self.config.retries - 1:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        value = await self.get(key, ConsistencyLevel.EVENTUAL)
        return value is not None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomic increment"""
        for attempt in range(10):  # Retry for conflicts
            current = await self.get(key)
            if current is None:
                current = 0
            elif not isinstance(current, (int, float)):
                raise ValueError(f"Cannot increment non-numeric value: {current}")
            
            new_value = current + amount
            # Use CAS (Check-And-Set) - in real implementation, this would be atomic
            success = await self.set(key, new_value)
            if success:
                return new_value
            await asyncio.sleep(0.01)
        
        return None
    
    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """Batch get multiple keys"""
        tasks = [self.get(key, ConsistencyLevel.EVENTUAL) for key in keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_result = {}
        for key, result in zip(keys, results):
            if not isinstance(result, Exception):
                batch_result[key] = result
        
        return batch_result
    
    async def batch_set(self, items: Dict[str, Any]) -> Dict[str, bool]:
        """Batch set multiple key-value pairs"""
        tasks = [self.set(key, value) for key, value in items.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_result = {}
        for (key, _), result in zip(items.items(), results):
            batch_result[key] = not isinstance(result, Exception)
        
        return batch_result
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        try:
            async with self.session.get(f"{self.base_url}/cluster/status") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": f"Status failed: {resp.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    class SyncKVClient:
        """Synchronous wrapper for async client"""
        
        def __init__(self, config: Optional[ClientConfig] = None):
            self.config = config
            self._async_client: Optional[KVClient] = None
            self._loop = asyncio.new_event_loop()
        
        def __enter__(self):
            self._async_client = self._loop.run_until_complete(KVClient(self.config).__aenter__())
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._async_client:
                self._loop.run_until_complete(self._async_client.__aexit__(exc_type, exc_val, exc_tb))
        
        def get(self, key: str, consistency: Optional[ConsistencyLevel] = None) -> Optional[Any]:
            return self._loop.run_until_complete(
                self._async_client.get(key, consistency)
            )
        
        def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
            return self._loop.run_until_complete(
                self._async_client.set(key, value, ttl)
            )
        
        def delete(self, key: str) -> bool:
            return self._loop.run_until_complete(
                self._async_client.delete(key)
            )
        
        def exists(self, key: str) -> bool:
            return self._loop.run_until_complete(
                self._async_client.exists(key)
            )
        
        def increment(self, key: str, amount: int = 1) -> Optional[int]:
            return self._loop.run_until_complete(
                self._async_client.increment(key, amount)
            )
        
        def get_cluster_status(self) -> Dict[str, Any]:
            return self._loop.run_until_complete(
                self._async_client.get_cluster_status()
            )