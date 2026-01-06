"""
TTL (Time-To-Live) Manager with Hierarchical Timing Wheels
"""
import asyncio
import time
from typing import Dict, List, Callable, Optional
from heapq import heappush, heappop
from dataclasses import dataclass
import threading

@dataclass(order=True)
class TTLItem:
    expiry: float
    key: str = ""
    callback: Optional[Callable] = None

class HierarchicalTimingWheel:
    """
    Efficient TTL management using hierarchical timing wheels
    O(1) for insert/delete, O(1) amortized for expiration
    """
    
    def __init__(self, tick_ms: int = 1000, wheel_size: int = 60):
        self.tick_ms = tick_ms
        self.wheel_size = wheel_size
        self.current_tick = 0
        
        # Create wheels (seconds, minutes, hours)
        self.second_wheel: List[List[TTLItem]] = [[] for _ in range(60)]
        self.minute_wheel: List[List[TTLItem]] = [[] for _ in range(60)]
        self.hour_wheel: List[List[TTLItem]] = [[] for _ in range(24)]
        
        self.lock = threading.RLock()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the timing wheel"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def stop(self):
        """Stop the timing wheel"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()
    
    def add(self, key: str, ttl_seconds: int, callback: Callable):
        """Add a key with TTL"""
        with self.lock:
            expiry = time.time() + ttl_seconds
            item = TTLItem(expiry=expiry, key=key, callback=callback)
            
            # Determine which wheel to use
            if ttl_seconds < 60:  # Less than a minute
                slot = int((self.current_tick + ttl_seconds) % 60)
                self.second_wheel[slot].append(item)
            elif ttl_seconds < 3600:  # Less than an hour
                slot = int((ttl_seconds // 60) % 60)
                self.minute_wheel[slot].append(item)
            else:  # More than an hour
                slot = int((ttl_seconds // 3600) % 24)
                self.hour_wheel[slot].append(item)
    
    def _worker(self):
        """Background worker that ticks every second"""
        while self.running:
            time.sleep(1)
            self._tick()
    
    def _tick(self):
        """Process current tick"""
        with self.lock:
            # Process second wheel
            items = self.second_wheel[self.current_tick]
            for item in items:
                if time.time() >= item.expiry:
                    if item.callback:
                        try:
                            item.callback(item.key)
                        except:
                            pass
            self.second_wheel[self.current_tick] = []
            
            # Cascade from higher wheels
            if self.current_tick == 0:
                # Move items from minute wheel to second wheel
                minute_slot = (time.localtime().tm_min) % 60
                for item in self.minute_wheel[minute_slot]:
                    remaining = item.expiry - time.time()
                    if remaining < 60:
                        slot = int(remaining % 60)
                        self.second_wheel[slot].append(item)
                self.minute_wheel[minute_slot] = []
                
                # Cascade from hour wheel
                hour_slot = time.localtime().tm_hour % 24
                for item in self.hour_wheel[hour_slot]:
                    remaining = item.expiry - time.time()
                    if remaining < 3600:
                        slot = int((remaining // 60) % 60)
                        self.minute_wheel[slot].append(item)
                self.hour_wheel[hour_slot] = []
            
            self.current_tick = (self.current_tick + 1) % 60

class TTLManager:
    """Main TTL manager with multiple strategies"""
    
    def __init__(self):
        self.timing_wheel = HierarchicalTimingWheel()
        self.expiry_map: Dict[str, float] = {}  # key -> expiry time
        self.lock = threading.RLock()
        
        # Start background cleaner
        self.timing_wheel.start()
    
    def set_ttl(self, key: str, ttl_seconds: int, delete_callback: Callable):
        """Set TTL for a key"""
        with self.lock:
            expiry = time.time() + ttl_seconds
            self.expiry_map[key] = expiry
            self.timing_wheel.add(key, ttl_seconds, delete_callback)
    
    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key"""
        with self.lock:
            expiry = self.expiry_map.get(key)
            if expiry is None:
                return None
            
            remaining = expiry - time.time()
            return max(0, int(remaining))
    
    def remove_ttl(self, key: str):
        """Remove TTL for a key"""
        with self.lock:
            self.expiry_map.pop(key, None)
    
    def cleanup_expired(self) -> List[str]:
        """Clean up expired keys and return list of removed keys"""
        expired = []
        current_time = time.time()
        
        with self.lock:
            keys_to_remove = []
            for key, expiry in self.expiry_map.items():
                if current_time >= expiry:
                    keys_to_remove.append(key)
                    expired.append(key)
            
            for key in keys_to_remove:
                self.expiry_map.pop(key, None)
        
        return expired
    
    def get_stats(self) -> Dict[str, int]:
        """Get TTL statistics"""
        with self.lock:
            return {
                "total_keys_with_ttl": len(self.expiry_map),
                "expiring_soon": len([k for k, v in self.expiry_map.items() 
                                    if v - time.time() < 60])
            }