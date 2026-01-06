"""
Advanced Eviction Policies Implementation
"""
import time
from typing import Optional, Dict, Any, List
from collections import OrderedDict, defaultdict
import math
import random

class BaseEvictionPolicy:
    """Base class for all eviction policies"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.current_size = 0
        self.hits = 0
        self.misses = 0
    
    def access(self, key: str) -> Optional[Any]:
        """Record access to a key"""
        raise NotImplementedError
    
    def put(self, key: str, value: Any, size: int = 1) -> List[str]:
        """Put a key-value pair, returns evicted keys"""
        raise NotImplementedError
    
    def delete(self, key: str):
        """Delete a key"""
        raise NotImplementedError
    
    def get_hit_rate(self) -> float:
        """Calculate hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

class LRUPolicy(BaseEvictionPolicy):
    """Least Recently Used policy"""
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.cache = OrderedDict()
        self.sizes: Dict[str, int] = {}
    
    def access(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value
        else:
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any, size: int = 1) -> List[str]:
        evicted = []
        
        if key in self.cache:
            # Update existing key
            old_size = self.sizes.get(key, 1)
            self.current_size -= old_size
        
        # Check if we need to evict
        while self.current_size + size > self.max_size and self.cache:
            # Remove least recently used
            evicted_key, _ = self.cache.popitem(last=False)
            evicted_size = self.sizes.pop(evicted_key, 1)
            self.current_size -= evicted_size
            evicted.append(evicted_key)
        
        # Add new entry
        self.cache[key] = value
        self.sizes[key] = size
        self.current_size += size
        
        return evicted
    
    def delete(self, key: str):
        if key in self.cache:
            size = self.sizes.pop(key, 1)
            self.cache.pop(key)
            self.current_size -= size

class LFUPolicy(BaseEvictionPolicy):
    """Least Frequently Used policy with aging"""
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.cache: Dict[str, Any] = {}
        self.freq: Dict[str, int] = defaultdict(int)
        self.sizes: Dict[str, int] = {}
        self.min_freq = 0
        self.freq_lists: Dict[int, OrderedDict] = defaultdict(OrderedDict)
        self.current_size = 0
    
    def access(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Update frequency
            freq = self.freq[key]
            self.freq_lists[freq].pop(key)
            
            if freq == self.min_freq and not self.freq_lists[freq]:
                self.min_freq += 1
            
            new_freq = freq + 1
            self.freq[key] = new_freq
            self.freq_lists[new_freq][key] = self.cache[key]
            self.hits += 1
            return self.cache[key]
        else:
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any, size: int = 1) -> List[str]:
        evicted = []
        
        if key in self.cache:
            # Update existing
            old_size = self.sizes.get(key, 1)
            self.current_size -= old_size
            self.access(key)  # Update frequency
        else:
            # New key
            self.freq[key] = 1
            self.freq_lists[1][key] = value
            self.min_freq = 1
        
        self.cache[key] = value
        self.sizes[key] = size
        self.current_size += size
        
        # Evict if needed
        while self.current_size > self.max_size and self.cache:
            # Get keys with min frequency
            min_freq_list = self.freq_lists[self.min_freq]
            if min_freq_list:
                # Remove least recently used from min freq list
                evicted_key, _ = min_freq_list.popitem(last=False)
                evicted_size = self.sizes.pop(evicted_key, 1)
                self.freq.pop(evicted_key)
                self.cache.pop(evicted_key)
                self.current_size -= evicted_size
                evicted.append(evicted_key)
            else:
                self.min_freq += 1
        
        return evicted
    
    def delete(self, key: str):
        if key in self.cache:
            size = self.sizes.pop(key, 1)
            freq = self.freq.pop(key)
            self.freq_lists[freq].pop(key, None)
            self.cache.pop(key)
            self.current_size -= size

class ARCAdaptiveReplacement(BaseEvictionPolicy):
    """
    Adaptive Replacement Cache (ARC)
    Automatically balances between LRU and LFU
    """
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.p = 0  # Target size for T1
        self.t1 = OrderedDict()  # Recent cache entries
        self.b1 = OrderedDict()  # Recent evictions
        self.t2 = OrderedDict()  # Frequent entries
        self.b2 = OrderedDict()  # Frequent evictions
        self.cache = {}
        self.sizes = {}
        self.current_size = 0
    
    def access(self, key: str) -> Optional[Any]:
        if key in self.t1:
            # Move from T1 to T2 (promote to frequent)
            self.t1.pop(key)
            self.t2[key] = self.cache[key]
            self.hits += 1
            return self.cache[key]
        elif key in self.t2:
            # Refresh in T2
            self.t2.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        else:
            self.misses += 1
            return None
    
    def _replace(self, key: str, size: int) -> List[str]:
        """ARC replacement algorithm"""
        evicted = []
        
        # Check if we need to evict
        while self.current_size + size > self.max_size:
            if self.t1 and (
                len(self.t1) > self.p or 
                (key in self.b2 and len(self.t1) == self.p)
            ):
                # Evict from T1
                if self.t1:
                    evicted_key, _ = self.t1.popitem(last=False)
                    evicted_size = self.sizes.pop(evicted_key, 1)
                    self.b1[evicted_key] = True
                    self.cache.pop(evicted_key)
                    self.current_size -= evicted_size
                    evicted.append(evicted_key)
            else:
                # Evict from T2
                if self.t2:
                    evicted_key, _ = self.t2.popitem(last=False)
                    evicted_size = self.sizes.pop(evicted_key, 1)
                    self.b2[evicted_key] = True
                    self.cache.pop(evicted_key)
                    self.current_size -= evicted_size
                    evicted.append(evicted_key)
        
        return evicted
    
    def put(self, key: str, value: Any, size: int = 1) -> List[str]:
        evicted = self._replace(key, size)
        
        # Add to cache
        self.cache[key] = value
        self.sizes[key] = size
        self.current_size += size
        
        # Add to T1 (recent)
        self.t1[key] = value
        
        # Adaptive adjustment
        if key in self.b1:
            # Hit in B1: increase target size for T1
            self.p = min(self.p + max(1, len(self.b2) // len(self.b1)), self.max_size)
            self.b1.pop(key)
        elif key in self.b2:
            # Hit in B2: decrease target size for T1
            self.p = max(self.p - max(1, len(self.b1) // len(self.b2)), 0)
            self.b2.pop(key)
        
        return evicted
    
    def delete(self, key: str):
        if key in self.cache:
            size = self.sizes.pop(key, 1)
            self.t1.pop(key, None)
            self.t2.pop(key, None)
            self.b1.pop(key, None)
            self.b2.pop(key, None)
            self.cache.pop(key)
            self.current_size -= size

class AdaptiveEvictionManager:
    """Intelligent eviction policy manager that adapts to workload"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        
        # Multiple policies for different access patterns
        self.lru = LRUPolicy(max_size)
        self.lfu = LFUPolicy(max_size)
        self.arc = ARCAdaptiveReplacement(max_size)
        
        # Current active policy
        self.active_policy = self.arc  # Start with ARC
        
        # Workload analyzer
        self.access_pattern = "unknown"
        self.access_history = []
        self.pattern_history = []
        
        # Statistics
        self.total_accesses = 0
        self.policy_switches = 0
        
        # Start monitoring thread
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Monitor access patterns and adapt policy"""
        import threading
        
        def monitor():
            while True:
                time.sleep(60)  # Analyze every minute
                self._analyze_workload()
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _analyze_workload(self):
        """Analyze access pattern and switch policy if needed"""
        if len(self.access_history) < 100:
            return
        
        # Calculate metrics
        unique_keys = len(set(self.access_history[-1000:]))
        total_accesses = len(self.access_history[-1000:])
        
        # Determine pattern
        if unique_keys < 50 and total_accesses > 500:
            # Small working set, high reuse
            new_pattern = "temporal_locality"
            new_policy = self.lru
        elif unique_keys > 800:
            # Large working set, low reuse
            new_pattern = "scanning"
            new_policy = self.arc
        else:
            # Mixed pattern
            new_pattern = "mixed"
            new_policy = self.arc
        
        # Switch policy if pattern changed
        if new_pattern != self.access_pattern:
            self.access_pattern = new_pattern
            self.active_policy = new_policy
            self.policy_switches += 1
            print(f"Switched to {new_pattern} pattern, using {new_policy.__class__.__name__}")
    
    def access(self, key: str) -> Optional[Any]:
        """Record access and return value"""
        self.total_accesses += 1
        self.access_history.append(key)
        return self.active_policy.access(key)
    
    def put(self, key: str, value: Any, size: int = 1) -> List[str]:
        """Put value with adaptive eviction"""
        return self.active_policy.put(key, value, size)
    
    def delete(self, key: str):
        """Delete key from all policies"""
        self.lru.delete(key)
        self.lfu.delete(key)
        self.arc.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            "active_policy": self.active_policy.__class__.__name__,
            "access_pattern": self.access_pattern,
            "total_accesses": self.total_accesses,
            "policy_switches": self.policy_switches,
            "lru_hit_rate": self.lru.get_hit_rate(),
            "lfu_hit_rate": self.lfu.get_hit_rate(),
            "arc_hit_rate": self.arc.get_hit_rate(),
            "current_size": self.active_policy.current_size,
            "max_size": self.max_size
        }