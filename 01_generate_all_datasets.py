"""
Generate Complete Datasets for Power BI Dashboard
This creates realistic data for a 7-day period with hourly metrics
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import os

# Create output directory
os.makedirs("powerbi/datasets", exist_ok=True)

def generate_cluster_metrics():
    """Generate cluster-level metrics over time"""
    print("Generating cluster_metrics.csv...")
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='1H')
    data = []
    
    # Base values that change over time
    total_nodes = 6
    replication_factor = 3
    
    for i, timestamp in enumerate(dates):
        # Simulate business patterns (weekday/weekend, day/night)
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        # Peak hours: 9 AM - 6 PM on weekdays
        is_peak = (weekday < 5) and (9 <= hour <= 18)
        
        # Base traffic
        if is_peak:
            base_ops = random.randint(8000, 12000)
        else:
            base_ops = random.randint(1000, 4000)
        
        # Add some trends and patterns
        trend_factor = 1 + (0.2 * np.sin(i / 24 * np.pi))  # Daily pattern
        
        total_ops = int(base_ops * trend_factor * (1 + random.uniform(-0.1, 0.1)))
        
        # Calculate other metrics
        successful_ops = int(total_ops * random.uniform(0.985, 0.998))
        failed_ops = total_ops - successful_ops
        
        # Latency varies by time
        if is_peak:
            avg_latency = random.uniform(8, 15)
            p95_latency = random.uniform(20, 35)
            p99_latency = random.uniform(40, 60)
        else:
            avg_latency = random.uniform(3, 8)
            p95_latency = random.uniform(10, 20)
            p99_latency = random.uniform(25, 40)
        
        # Node health (occasional failures)
        if random.random() < 0.01:  # 1% chance of node failure
            alive_nodes = total_nodes - 1
        else:
            alive_nodes = total_nodes
        
        # Storage usage grows over time
        base_storage = 100 * (1 + i/168)  # Grow over 7 days
        storage_used_gb = base_storage * (1 + random.uniform(-0.05, 0.05))
        storage_total_gb = 500
        
        # Network metrics
        network_in_mbps = total_ops * 0.5 * (1 + random.uniform(-0.2, 0.2))
        network_out_mbps = total_ops * 0.3 * (1 + random.uniform(-0.2, 0.2))
        
        # Cache metrics
        cache_hit_rate = random.uniform(0.85, 0.98) if is_peak else random.uniform(0.90, 0.99)
        
        data.append({
            'timestamp': timestamp,
            'total_operations_per_sec': total_ops,
            'successful_operations_per_sec': successful_ops,
            'failed_operations_per_sec': failed_ops,
            'availability_percentage': (alive_nodes / total_nodes) * 100,
            'avg_latency_ms': avg_latency,
            'p95_latency_ms': p95_latency,
            'p99_latency_ms': p99_latency,
            'total_nodes': total_nodes,
            'alive_nodes': alive_nodes,
            'storage_used_gb': storage_used_gb,
            'storage_total_gb': storage_total_gb,
            'storage_utilization_percent': (storage_used_gb / storage_total_gb) * 100,
            'network_in_mbps': network_in_mbps,
            'network_out_mbps': network_out_mbps,
            'cache_hit_rate_percent': cache_hit_rate * 100,
            'replication_factor': replication_factor,
            'data_durability_percent': 99.999 + random.uniform(-0.001, 0.001),
            'is_peak_hour': is_peak,
            'hour_of_day': hour,
            'day_of_week': weekday,
            'weekend': weekday >= 5
        })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/cluster_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_node_metrics():
    """Generate per-node detailed metrics"""
    print("Generating node_metrics.csv...")
    
    node_ids = ['node-us-east-1a-01', 'node-us-east-1b-02', 'node-us-east-1c-03',
                'node-us-west-2a-01', 'node-us-west-2b-02', 'node-eu-west-1a-01']
    regions = ['us-east-1', 'us-east-1', 'us-east-1', 
               'us-west-2', 'us-west-2', 'eu-west-1']
    zones = ['1a', '1b', '1c', '2a', '2b', '1a']
    shard_ids = ['shard-001', 'shard-002', 'shard-001', 
                 'shard-003', 'shard-004', 'shard-002']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='15min')
    data = []
    
    for timestamp in dates:
        hour = timestamp.hour
        is_peak = (timestamp.weekday() < 5) and (9 <= hour <= 18)
        
        for node_idx, node_id in enumerate(node_ids):
            # Base values per node
            base_ops = random.randint(500, 2000) if is_peak else random.randint(100, 500)
            
            # Add some node-specific characteristics
            if 'us-east' in node_id:
                base_ops *= 1.5  # US East handles more traffic
            if node_id.endswith('01'):
                base_ops *= 1.2  # Primary nodes get more traffic
            
            # Add randomness
            ops_per_sec = int(base_ops * (1 + random.uniform(-0.15, 0.15)))
            
            # CPU usage correlates with operations
            cpu_percent = min(100, 20 + (ops_per_sec / 50) * random.uniform(0.8, 1.2))
            
            # Memory usage
            memory_percent = random.uniform(40, 80)
            
            # Disk I/O
            disk_read_mbps = ops_per_sec * 0.2 * random.uniform(0.8, 1.2)
            disk_write_mbps = ops_per_sec * 0.3 * random.uniform(0.8, 1.2)
            
            # Network
            network_in = ops_per_sec * 0.08 * random.uniform(0.8, 1.2)
            network_out = ops_per_sec * 0.05 * random.uniform(0.8, 1.2)
            
            # Node health (occasional issues)
            is_healthy = random.random() > 0.005  # 0.5% chance of unhealthy
            last_heartbeat_seconds = 0 if is_healthy else random.randint(10, 300)
            
            # Leadership status (some nodes are leaders for their shard)
            is_leader = (node_idx % 3 == 0)  # Every 3rd node is a leader
            
            # Replication lag (in milliseconds)
            replication_lag_ms = 0 if is_leader else random.randint(1, 50)
            
            # Cache performance
            cache_hit_rate = random.uniform(0.85, 0.98)
            
            # Errors
            error_count = int(ops_per_sec * 0.001 * random.uniform(0.5, 1.5))
            
            data.append({
                'timestamp': timestamp,
                'node_id': node_id,
                'region': regions[node_idx],
                'availability_zone': zones[node_idx],
                'shard_id': shard_ids[node_idx],
                'operations_per_sec': ops_per_sec,
                'cpu_utilization_percent': cpu_percent,
                'memory_utilization_percent': memory_percent,
                'disk_usage_percent': random.uniform(30, 70),
                'disk_read_mbps': disk_read_mbps,
                'disk_write_mbps': disk_write_mbps,
                'network_in_mbps': network_in,
                'network_out_mbps': network_out,
                'is_healthy': is_healthy,
                'last_heartbeat_seconds': last_heartbeat_seconds,
                'is_leader': is_leader,
                'replication_lag_ms': replication_lag_ms,
                'cache_hit_rate_percent': cache_hit_rate * 100,
                'error_count': error_count,
                'connections': random.randint(50, 500),
                'key_count': random.randint(1000000, 5000000),
                'data_size_gb': random.uniform(20, 100)
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/node_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_request_metrics():
    """Generate detailed request/operation metrics"""
    print("Generating request_metrics.csv...")
    
    operation_types = ['GET', 'PUT', 'DELETE', 'SCAN', 'INCR']
    consistency_levels = ['STRONG', 'QUORUM', 'EVENTUAL']
    client_types = ['web_server', 'mobile_app', 'batch_job', 'analytics', 'api_gateway']
    
    # Create 24 hours of data
    dates = pd.date_range(start='2024-01-07', periods=24, freq='1H')
    data = []
    
    for timestamp in dates:
        hour = timestamp.hour
        is_peak = 9 <= hour <= 18
        
        for op_type in operation_types:
            # Base volume by operation type
            base_volume = {
                'GET': 8000 if is_peak else 2000,
                'PUT': 2000 if is_peak else 500,
                'DELETE': 500 if is_peak else 100,
                'SCAN': 300 if is_peak else 50,
                'INCR': 1000 if is_peak else 200
            }[op_type]
            
            # Add hourly pattern
            hourly_factor = 1 + 0.3 * np.sin((hour - 12) / 12 * np.pi)
            volume = int(base_volume * hourly_factor * random.uniform(0.9, 1.1))
            
            for consistency in consistency_levels:
                # Distribution of consistency levels
                consistency_dist = {
                    'STRONG': 0.3,
                    'QUORUM': 0.5,
                    'EVENTUAL': 0.2
                }
                
                consistency_volume = int(volume * consistency_dist[consistency])
                
                # Latency varies by operation and consistency
                latency_base = {
                    'GET': {'STRONG': 5, 'QUORUM': 3, 'EVENTUAL': 1},
                    'PUT': {'STRONG': 8, 'QUORUM': 5, 'EVENTUAL': 2},
                    'DELETE': {'STRONG': 7, 'QUORUM': 4, 'EVENTUAL': 1.5},
                    'SCAN': {'STRONG': 50, 'QUORUM': 30, 'EVENTUAL': 10},
                    'INCR': {'STRONG': 6, 'QUORUM': 4, 'EVENTUAL': 2}
                }[op_type][consistency]
                
                avg_latency = latency_base * (1 + random.uniform(-0.2, 0.2))
                
                # Error rate varies
                error_rate = random.uniform(0.001, 0.01) if is_peak else random.uniform(0.0001, 0.001)
                
                data.append({
                    'timestamp': timestamp,
                    'operation_type': op_type,
                    'consistency_level': consistency,
                    'request_count': consistency_volume,
                    'avg_latency_ms': avg_latency,
                    'p95_latency_ms': avg_latency * random.uniform(2, 4),
                    'p99_latency_ms': avg_latency * random.uniform(3, 6),
                    'error_count': int(consistency_volume * error_rate),
                    'success_count': consistency_volume - int(consistency_volume * error_rate),
                    'error_rate_percent': error_rate * 100,
                    'data_transferred_mb': consistency_volume * random.uniform(0.01, 0.1),
                    'is_peak_hour': is_peak,
                    'hour_of_day': hour
                })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/request_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_shard_metrics():
    """Generate shard-level distribution and performance metrics"""
    print("Generating shard_metrics.csv...")
    
    shard_ids = ['shard-001', 'shard-002', 'shard-003', 'shard-004', 'shard-005']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='2H')
    data = []
    
    # Initial distribution
    key_distribution = {
        'shard-001': 1500000,
        'shard-002': 1200000,
        'shard-003': 1800000,
        'shard-004': 900000,
        'shard-005': 1400000
    }
    
    size_distribution = {
        'shard-001': 45.2,
        'shard-002': 38.7,
        'shard-003': 52.1,
        'shard-004': 28.9,
        'shard-005': 42.3
    }
    
    for timestamp in dates:
        hour = timestamp.hour
        is_peak = (timestamp.weekday() < 5) and (9 <= hour <= 18)
        
        for shard_id in shard_ids:
            # Simulate growth over time
            days_since_start = (timestamp - dates[0]).days
            growth_factor = 1 + (days_since_start * 0.02)
            
            # Key count grows
            key_count = int(key_distribution[shard_id] * growth_factor * random.uniform(0.99, 1.01))
            
            # Size grows proportionally
            size_gb = size_distribution[shard_id] * growth_factor * random.uniform(0.99, 1.01)
            
            # Operations vary by shard
            if is_peak:
                ops_per_sec = random.randint(800, 2000)
            else:
                ops_per_sec = random.randint(200, 600)
            
            # Shard 001 gets more traffic (hot shard)
            if shard_id == 'shard-001':
                ops_per_sec = int(ops_per_sec * 1.5)
            
            # Replica status
            replica_count = 3
            healthy_replicas = random.choice([2, 3])  # Sometimes 1 replica is down
            
            # Load balancing metrics
            load_imbalance_percent = random.uniform(0, 20)
            
            # Eviction metrics (for cache/memory pressure)
            eviction_rate = random.uniform(0.1, 2.0) if is_peak else random.uniform(0.01, 0.5)
            
            # Hot key detection
            hot_key_count = int(key_count * random.uniform(0.0001, 0.001))
            
            data.append({
                'timestamp': timestamp,
                'shard_id': shard_id,
                'key_count': key_count,
                'data_size_gb': size_gb,
                'operations_per_sec': ops_per_sec,
                'avg_latency_ms': random.uniform(3, 15),
                'replica_count': replica_count,
                'healthy_replicas': healthy_replicas,
                'replication_status': 'HEALTHY' if healthy_replicas == replica_count else 'DEGRADED',
                'load_imbalance_percent': load_imbalance_percent,
                'eviction_rate_per_sec': eviction_rate,
                'hot_key_count': hot_key_count,
                'cold_key_count': int(key_count * 0.7),  # 70% of keys are rarely accessed
                'ttl_expirations_per_sec': random.uniform(10, 100),
                'compaction_ongoing': random.random() < 0.1,  # 10% chance compaction is running
                'disk_usage_percent': random.uniform(40, 80)
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/shard_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_client_metrics():
    """Generate client/application usage metrics"""
    print("Generating client_metrics.csv...")
    
    client_ids = ['web-app-prod', 'mobile-app-prod', 'batch-processing', 
                  'analytics-platform', 'api-service', 'data-pipeline']
    departments = ['E-commerce', 'Mobile', 'Data Engineering', 'Analytics', 'Platform', 'Data Engineering']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='1H')
    data = []
    
    for timestamp in dates:
        hour = timestamp.hour
        weekday = timestamp.weekday()
        is_peak = (weekday < 5) and (9 <= hour <= 18)
        
        for client_idx, client_id in enumerate(client_ids):
            # Base usage by client
            base_usage = {
                'web-app-prod': 4000 if is_peak else 800,
                'mobile-app-prod': 3000 if is_peak else 600,
                'batch-processing': 500,
                'analytics-platform': 800 if is_peak else 200,
                'api-service': 2000 if is_peak else 400,
                'data-pipeline': 300
            }[client_id]
            
            # Add patterns
            if client_id == 'web-app-prod':
                # Web traffic peaks during business hours
                pattern_factor = 1 + 0.5 * np.sin((hour - 14) / 12 * np.pi)
            elif client_id == 'mobile-app-prod':
                # Mobile traffic more evenly distributed
                pattern_factor = 1 + 0.3 * np.sin((hour - 20) / 12 * np.pi)
            elif client_id == 'batch-processing':
                # Batch jobs run at night
                pattern_factor = 3 if hour in [2, 3, 4] else 0.5
            else:
                pattern_factor = 1
            
            request_count = int(base_usage * pattern_factor * random.uniform(0.8, 1.2))
            
            # Data transferred
            avg_value_size_kb = {
                'web-app-prod': 2.5,
                'mobile-app-prod': 1.8,
                'batch-processing': 50.0,
                'analytics-platform': 10.0,
                'api-service': 5.0,
                'data-pipeline': 100.0
            }[client_id]
            
            data_transferred_mb = (request_count * avg_value_size_kb) / 1024
            
            # Latency SLA compliance
            sla_latency_ms = 50  # 50ms SLA
            avg_latency = random.uniform(10, 40)
            sla_compliance = 100 if avg_latency < sla_latency_ms else random.uniform(95, 99.9)
            
            # Error rate
            error_rate = random.uniform(0.001, 0.01) if is_peak else random.uniform(0.0005, 0.002)
            
            # Cost (per million requests)
            cost_per_million = random.uniform(0.50, 2.00)
            cost = (request_count / 1000000) * cost_per_million
            
            data.append({
                'timestamp': timestamp,
                'client_id': client_id,
                'department': departments[client_idx],
                'request_count': request_count,
                'avg_latency_ms': avg_latency,
                'data_transferred_mb': data_transferred_mb,
                'error_count': int(request_count * error_rate),
                'error_rate_percent': error_rate * 100,
                'sla_compliance_percent': sla_compliance,
                'cost_usd': cost,
                'cache_hit_rate_percent': random.uniform(85, 98),
                'connection_count': random.randint(10, 200),
                'is_peak_hour': is_peak,
                'hour_of_day': hour,
                'day_of_week': weekday
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/client_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_eviction_metrics():
    """Generate cache eviction policy performance metrics"""
    print("Generating eviction_metrics.csv...")
    
    policies = ['ARC', 'LRU', 'LFU', 'W-TinyLFU', 'Adaptive']
    access_patterns = ['temporal_locality', 'scanning', 'zipfian', 'mixed', 'random']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='30min')
    data = []
    
    for timestamp in dates:
        hour = timestamp.hour
        is_peak = (timestamp.weekday() < 5) and (9 <= hour <= 18)
        
        for policy in policies:
            # Base hit rate varies by policy
            base_hit_rate = {
                'ARC': 0.92,
                'LRU': 0.88,
                'LFU': 0.85,
                'W-TinyLFU': 0.94,
                'Adaptive': 0.96
            }[policy]
            
            # Adaptive policy performs best during peaks
            if policy == 'Adaptive' and is_peak:
                hit_rate = base_hit_rate * 1.05
            else:
                hit_rate = base_hit_rate * random.uniform(0.98, 1.02)
            
            hit_rate = min(0.99, hit_rate)  # Cap at 99%
            
            # Eviction rate
            eviction_rate = random.uniform(0.5, 5.0) if is_peak else random.uniform(0.1, 1.0)
            
            # Memory usage
            memory_usage_percent = random.uniform(60, 95)
            
            # Policy switches (for adaptive policy)
            policy_switches = 0
            if policy == 'Adaptive':
                policy_switches = random.randint(0, 3)
            
            # Cost metrics (memory vs performance trade-off)
            cost_per_hit_ms = random.uniform(0.01, 0.05)  # Cost per cache hit in ms
            
            data.append({
                'timestamp': timestamp,
                'eviction_policy': policy,
                'cache_hit_rate_percent': hit_rate * 100,
                'cache_miss_rate_percent': (1 - hit_rate) * 100,
                'eviction_rate_per_sec': eviction_rate,
                'memory_usage_percent': memory_usage_percent,
                'avg_access_time_ms': random.uniform(0.1, 0.5),
                'policy_switches': policy_switches,
                'active_access_pattern': random.choice(access_patterns),
                'cost_per_hit_ms': cost_per_hit_ms,
                'total_cost_ms': cost_per_hit_ms * 1000,  # Estimated per 1000 hits
                'cache_size_mb': 1024,  # 1GB cache
                'items_cached': random.randint(500000, 2000000),
                'is_peak_hour': is_peak
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/eviction_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_replication_metrics():
    """Generate replication and consistency metrics"""
    print("Generating replication_metrics.csv...")
    
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='15min')
    data = []
    
    for timestamp in dates:
        hour = timestamp.hour
        is_peak = (timestamp.weekday() < 5) and (9 <= hour <= 18)
        
        for region in regions:
            # Replication lag varies by region distance
            base_lag = {
                'us-east-1': 5,      # Primary region
                'us-west-2': 15,     # Cross-US
                'eu-west-1': 50,     # Cross-Atlantic
                'ap-southeast-1': 100 # Cross-Pacific
            }[region]
            
            # Add network variability
            replication_lag_ms = base_lag * random.uniform(0.8, 1.5)
            
            # Replication throughput
            if is_peak:
                replication_mbps = random.uniform(50, 200)
            else:
                replication_mbps = random.uniform(20, 100)
            
            # Consistency violations (rare)
            consistency_violations = 0
            if random.random() < 0.001:  # 0.1% chance of violation
                consistency_violations = random.randint(1, 5)
            
            # Data durability
            durability_percent = 99.999 + random.uniform(-0.001, 0.001)
            
            # Raft consensus metrics
            raft_term = random.randint(100, 500)
            leader_elections = random.randint(0, 3)
            
            # Network partitions (rare events)
            network_partition = random.random() < 0.0005  # 0.05% chance
            
            data.append({
                'timestamp': timestamp,
                'region': region,
                'replication_lag_ms': replication_lag_ms,
                'replication_throughput_mbps': replication_mbps,
                'replication_queue_size': random.randint(0, 1000),
                'consistency_violations': consistency_violations,
                'data_durability_percent': durability_percent,
                'raft_term': raft_term,
                'leader_elections': leader_elections,
                'network_partition_detected': network_partition,
                'bytes_replicated_gb': random.uniform(100, 500),
                'replication_connections': random.randint(10, 50),
                'is_primary_region': region == 'us-east-1',
                'sync_status': 'IN_SYNC' if replication_lag_ms < 100 else 'LAGGING',
                'is_peak_hour': is_peak
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/replication_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_cost_metrics():
    """Generate cost and resource optimization metrics"""
    print("Generating cost_metrics.csv...")
    
    cost_categories = ['Compute', 'Storage', 'Network', 'Cache', 'Backup', 'Monitoring']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='1D')
    data = []
    
    total_cost = 0
    
    for timestamp in dates:
        # Daily costs with some variation
        daily_base_cost = 500  # Base cost per day
        
        for category in cost_categories:
            # Cost distribution by category
            category_share = {
                'Compute': 0.40,
                'Storage': 0.25,
                'Network': 0.15,
                'Cache': 0.10,
                'Backup': 0.05,
                'Monitoring': 0.05
            }[category]
            
            base_cost = daily_base_cost * category_share
            
            # Add some daily variation
            daily_variation = random.uniform(0.9, 1.1)
            cost = base_cost * daily_variation
            
            # Efficiency metrics
            if category == 'Compute':
                efficiency = random.uniform(75, 95)  # CPU utilization %
                savings_opportunity = random.uniform(100, 500)
            elif category == 'Storage':
                efficiency = random.uniform(60, 85)  # Storage utilization %
                savings_opportunity = random.uniform(50, 300)
            elif category == 'Network':
                efficiency = random.uniform(80, 98)  # Network utilization %
                savings_opportunity = random.uniform(20, 150)
            else:
                efficiency = random.uniform(85, 99)
                savings_opportunity = random.uniform(10, 100)
            
            total_cost += cost
            
            data.append({
                'date': timestamp.date(),
                'cost_category': category,
                'daily_cost_usd': cost,
                'monthly_projected_usd': cost * 30,
                'cost_efficiency_percent': efficiency,
                'savings_opportunity_usd': savings_opportunity,
                'resource_utilization_percent': random.uniform(70, 95),
                'cost_per_request_usd': cost / 1000000,  # Cost per million requests
                'cost_trend': 'STABLE' if random.random() < 0.7 else ('INCREASING' if random.random() < 0.5 else 'DECREASING'),
                'optimization_recommendation': random.choice([
                    'Scale down during off-peak',
                    'Implement compression',
                    'Use cheaper storage tier',
                    'Optimize cache sizing',
                    'Reduce cross-region traffic'
                ])
            })
    
    # Add total row
    data.append({
        'date': dates[-1].date(),
        'cost_category': 'TOTAL',
        'daily_cost_usd': total_cost,
        'monthly_projected_usd': total_cost * 30,
        'cost_efficiency_percent': random.uniform(80, 90),
        'savings_opportunity_usd': random.uniform(500, 2000),
        'resource_utilization_percent': random.uniform(75, 85),
        'cost_per_request_usd': total_cost / 5000000,  # Rough estimate
        'cost_trend': 'INCREASING',
        'optimization_recommendation': 'Review all optimization opportunities'
    })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/cost_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_incident_log():
    """Generate incident and alert log"""
    print("Generating incident_log.csv...")
    
    incident_types = ['Node Failure', 'High Latency', 'Network Partition', 
                      'Storage Full', 'Replication Lag', 'Memory Pressure', 
                      'Cache Eviction Storm', 'Leader Election', 'TTL Expiration Storm']
    
    severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    statuses = ['RESOLVED', 'IN_PROGRESS', 'INVESTIGATING', 'ACKNOWLEDGED']
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='6H')
    data = []
    
    incident_id = 1000
    
    for timestamp in dates:
        # 30% chance of incident each 6-hour period
        if random.random() < 0.3:
            incident_type = random.choice(incident_types)
            severity = random.choice(severities)
            
            # Duration in minutes
            duration_minutes = random.randint(5, 120) if severity == 'CRITICAL' else random.randint(1, 30)
            
            # Affected components
            if incident_type == 'Node Failure':
                affected_nodes = random.randint(1, 2)
                affected_shards = random.randint(1, 3)
            elif incident_type == 'Network Partition':
                affected_nodes = random.randint(2, 4)
                affected_shards = random.randint(2, 5)
            else:
                affected_nodes = 1
                affected_shards = 1
            
            # Impact metrics
            requests_affected = random.randint(1000, 100000)
            latency_spike_percent = random.randint(50, 500)
            
            # Resolution
            status = random.choice(statuses)
            resolved_by = random.choice(['SRE Team', 'Auto-Recovery', 'System', 'On-call Engineer'])
            
            # Root cause
            root_cause = random.choice([
                'Hardware failure',
                'Network congestion',
                'Software bug',
                'Configuration error',
                'Resource exhaustion',
                'Deployment issue',
                'External dependency'
            ])
            
            data.append({
                'incident_id': f'INC-{incident_id}',
                'timestamp': timestamp,
                'incident_type': incident_type,
                'severity': severity,
                'status': status,
                'duration_minutes': duration_minutes,
                'affected_nodes': affected_nodes,
                'affected_shards': affected_shards,
                'requests_affected': requests_affected,
                'latency_spike_percent': latency_spike_percent,
                'availability_impact_percent': random.uniform(0.1, 5.0),
                'resolved_by': resolved_by,
                'root_cause': root_cause,
                'resolution_action': f'Fixed {root_cause.lower()}',
                'prevention_action': random.choice([
                    'Add monitoring',
                    'Increase capacity',
                    'Update configuration',
                    'Fix software bug',
                    'Improve failover'
                ]),
                'sla_violation': severity in ['CRITICAL', 'HIGH'],
                'cost_impact_usd': random.uniform(100, 5000)
            })
            
            incident_id += 1
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/incident_log.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_benchmark_comparison():
    """Generate benchmark comparison data vs Redis, DynamoDB, etc."""
    print("Generating benchmark_comparison.csv...")
    
    systems = ['KV Store (Ours)', 'Redis Cluster', 'DynamoDB', 'Cassandra', 'etcd']
    
    metrics = ['Throughput', 'Latency', 'Cost', 'Durability', 'Consistency', 'Scalability']
    
    data = []
    
    for system in systems:
        for metric in metrics:
            # Score out of 10
            if system == 'KV Store (Ours)':
                score = random.uniform(8.5, 9.5)
            elif system == 'Redis Cluster':
                score = random.uniform(7.0, 8.5)
            elif system == 'DynamoDB':
                score = random.uniform(8.0, 9.0)
            elif system == 'Cassandra':
                score = random.uniform(7.5, 8.5)
            else:  # etcd
                score = random.uniform(6.0, 7.5)
            
            # Add some specific strengths/weaknesses
            if system == 'KV Store (Ours)' and metric == 'Cost':
                score = 9.0  # Our system is cost-effective
            elif system == 'DynamoDB' and metric == 'Cost':
                score = 6.5  # DynamoDB can be expensive
            
            # Value based on metric
            if metric == 'Throughput':
                value = f"{random.randint(50000, 150000):,} ops/sec"
            elif metric == 'Latency':
                value = f"{random.uniform(1, 10):.1f} ms"
            elif metric == 'Cost':
                value = f"${random.uniform(0.1, 2.0):.2f}/M ops"
            elif metric == 'Durability':
                value = f"{random.uniform(99.9, 99.999):.3f}%"
            elif metric == 'Consistency':
                value = random.choice(['Strong', 'Eventual', 'Both'])
            elif metric == 'Scalability':
                value = f"{random.randint(10, 1000):,} nodes"
            
            data.append({
                'system': system,
                'metric': metric,
                'score': score,
                'value': value,
                'category': 'Performance' if metric in ['Throughput', 'Latency'] else 
                           'Cost' if metric == 'Cost' else 'Reliability',
                'is_our_system': system == 'KV Store (Ours)'
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/benchmark_comparison.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_key_pattern_analysis():
    """Generate key access pattern analysis"""
    print("Generating key_pattern_analysis.csv...")
    
    key_patterns = ['user:{id}:profile', 'session:{token}', 'product:{sku}:cache',
                    'order:{id}', 'cart:{user_id}', 'analytics:{date}:{metric}',
                    'config:{service}:{key}', 'cache:{hash}', 'lock:{resource}']
    
    data = []
    
    for pattern in key_patterns:
        # Estimate total keys with this pattern
        total_keys = random.randint(100000, 5000000)
        
        # Access patterns
        read_write_ratio = random.uniform(0.1, 10.0)  # Some are read-heavy, some write-heavy
        
        # Hot keys (top 1% get 80% of traffic)
        hot_key_percent = 1.0
        hot_key_traffic_percent = 80.0
        
        # TTL distribution
        avg_ttl_hours = random.uniform(1, 720)  # 1 hour to 30 days
        
        # Size distribution
        avg_value_size_kb = random.uniform(0.1, 50.0)
        
        # Access frequency
        accesses_per_day = random.randint(1000, 1000000)
        
        # Cache effectiveness
        cache_hit_rate = random.uniform(0.7, 0.99)
        
        data.append({
            'key_pattern': pattern,
            'total_keys': total_keys,
            'read_write_ratio': read_write_ratio,
            'hot_key_percent': hot_key_percent,
            'hot_key_traffic_percent': hot_key_traffic_percent,
            'avg_ttl_hours': avg_ttl_hours,
            'avg_value_size_kb': avg_value_size_kb,
            'accesses_per_day': accesses_per_day,
            'cache_hit_rate_percent': cache_hit_rate * 100,
            'shard_distribution': random.choice(['Uniform', 'Skewed', 'Concentrated']),
            'compression_ratio': random.uniform(1.5, 3.0),
            'optimization_recommendation': random.choice([
                'Increase TTL',
                'Add secondary index',
                'Implement compression',
                'Move to colder storage',
                'Add cache layer'
            ]),
            'estimated_savings_usd': random.uniform(100, 5000)
        })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/key_pattern_analysis.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def generate_geographic_metrics():
    """Generate geographic distribution metrics"""
    print("Generating geographic_metrics.csv...")
    
    regions = [
        {'region': 'North America', 'country': 'USA', 'city': 'Virginia', 'data_center': 'us-east-1'},
        {'region': 'North America', 'country': 'USA', 'city': 'Oregon', 'data_center': 'us-west-2'},
        {'region': 'Europe', 'country': 'Ireland', 'city': 'Dublin', 'data_center': 'eu-west-1'},
        {'region': 'Asia Pacific', 'country': 'Singapore', 'city': 'Singapore', 'data_center': 'ap-southeast-1'},
        {'region': 'Asia Pacific', 'country': 'Japan', 'city': 'Tokyo', 'data_center': 'ap-northeast-1'},
        {'region': 'South America', 'country': 'Brazil', 'city': 'São Paulo', 'data_center': 'sa-east-1'}
    ]
    
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='3H')
    data = []
    
    for timestamp in dates:
        hour = timestamp.hour
        for loc in regions:
            # Timezone-aware traffic patterns
            local_hour = (hour + {
                'us-east-1': 0,
                'us-west-2': -3,
                'eu-west-1': 5,
                'ap-southeast-1': 13,
                'ap-northeast-1': 14,
                'sa-east-1': 2
            }[loc['data_center']]) % 24
            
            is_local_peak = 9 <= local_hour <= 18
            
            # Traffic volume
            if is_local_peak:
                requests_per_sec = random.randint(1000, 5000)
            else:
                requests_per_sec = random.randint(200, 1000)
            
            # Latency to other regions
            latency_matrix = {
                'us-east-1': {'us-east-1': 1, 'us-west-2': 50, 'eu-west-1': 80, 'ap-southeast-1': 200, 'ap-northeast-1': 180, 'sa-east-1': 120},
                'us-west-2': {'us-east-1': 50, 'us-west-2': 1, 'eu-west-1': 150, 'ap-southeast-1': 150, 'ap-northeast-1': 120, 'sa-east-1': 180},
                'eu-west-1': {'us-east-1': 80, 'us-west-2': 150, 'eu-west-1': 1, 'ap-southeast-1': 200, 'ap-northeast-1': 220, 'sa-east-1': 180},
                'ap-southeast-1': {'us-east-1': 200, 'us-west-2': 150, 'eu-west-1': 200, 'ap-southeast-1': 1, 'ap-northeast-1': 60, 'sa-east-1': 300},
                'ap-northeast-1': {'us-east-1': 180, 'us-west-2': 120, 'eu-west-1': 220, 'ap-southeast-1': 60, 'ap-northeast-1': 1, 'sa-east-1': 280},
                'sa-east-1': {'us-east-1': 120, 'us-west-2': 180, 'eu-west-1': 180, 'ap-southeast-1': 300, 'ap-northeast-1': 280, 'sa-east-1': 1}
            }
            
            avg_cross_region_latency = np.mean(list(latency_matrix[loc['data_center']].values()))
            
            data.append({
                'timestamp': timestamp,
                'region': loc['region'],
                'country': loc['country'],
                'city': loc['city'],
                'data_center': loc['data_center'],
                'local_hour': local_hour,
                'requests_per_sec': requests_per_sec,
                'data_transferred_mbps': requests_per_sec * random.uniform(0.05, 0.2),
                'avg_latency_ms': random.uniform(1, 10) if is_local_peak else random.uniform(0.5, 5),
                'avg_cross_region_latency_ms': avg_cross_region_latency,
                'replication_lag_ms': random.uniform(5, 100),
                'node_count': random.randint(2, 6),
                'storage_used_tb': random.uniform(10, 100),
                'cost_per_gb': random.uniform(0.02, 0.10),
                'carbon_footprint_kg': requests_per_sec * random.uniform(0.0001, 0.001),
                'renewable_energy_percent': random.uniform(50, 100),
                'is_local_peak': is_local_peak
            })
    
    df = pd.DataFrame(data)
    df.to_csv('powerbi/datasets/geographic_metrics.csv', index=False)
    print(f"✓ Generated {len(df)} records")
    return df

def main():
    """Generate all datasets"""
    print("=" * 60)
    print("Generating Power BI Datasets for Distributed KV Store")
    print("=" * 60)
    
    # Generate all datasets
    cluster_df = generate_cluster_metrics()
    node_df = generate_node_metrics()
    request_df = generate_request_metrics()
    shard_df = generate_shard_metrics()
    client_df = generate_client_metrics()
    eviction_df = generate_eviction_metrics()
    replication_df = generate_replication_metrics()
    cost_df = generate_cost_metrics()
    incident_df = generate_incident_log()
    benchmark_df = generate_benchmark_comparison()
    key_pattern_df = generate_key_pattern_analysis()
    geographic_df = generate_geographic_metrics()
    
    # Create dataset summary
    summary = {
        'dataset': [
            'cluster_metrics', 'node_metrics', 'request_metrics', 'shard_metrics',
            'client_metrics', 'eviction_metrics', 'replication_metrics', 'cost_metrics',
            'incident_log', 'benchmark_comparison', 'key_pattern_analysis', 'geographic_metrics'
        ],
        'records': [
            len(cluster_df), len(node_df), len(request_df), len(shard_df),
            len(client_df), len(eviction_df), len(replication_df), len(cost_df),
            len(incident_df), len(benchmark_df), len(key_pattern_df), len(geographic_df)
        ],
        'time_range': ['7 days'] * 8 + ['N/A'] * 4,
        'update_frequency': ['1 hour', '15 min', '1 hour', '2 hours', 
                           '1 hour', '30 min', '15 min', '1 day',
                           '6 hours', 'Static', 'Static', '3 hours'],
        'description': [
            'Overall cluster performance and health',
            'Per-node resource utilization and metrics',
            'Request/operation type analysis',
            'Shard distribution and load balancing',
            'Client/application usage patterns',
            'Cache eviction policy performance',
            'Replication and consistency metrics',
            'Cost analysis and optimization',
            'Incident and alert history',
            'Comparison with other systems',
            'Key access pattern analysis',
            'Geographic distribution metrics'
        ]
    }
    
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv('powerbi/datasets/dataset_summary.csv', index=False)
    
    print("\n" + "=" * 60)
    print("DATASET GENERATION COMPLETE")
    print("=" * 60)
    print(f"Total datasets generated: {len(summary_df)}")
    print(f"Total records: {summary_df['records'].sum():,}")
    print(f"Output directory: powerbi/datasets/")
    print("\n  Dataset Summary:")
    print(summary_df.to_string())
    
    # Create README
    with open('powerbi/datasets/README.md', 'w') as f:
        f.write("# Power BI Datasets for Distributed KV Store\n\n")
        f.write("## Overview\n")
        f.write("These datasets simulate 7 days of operation for a distributed key-value store.\n\n")
        f.write("## Datasets\n\n")
        for _, row in summary_df.iterrows():
            f.write(f"### {row['dataset']}.csv\n")
            f.write(f"- **Records**: {row['records']:,}\n")
            f.write(f"- **Time Range**: {row['time_range']}\n")
            f.write(f"- **Update Frequency**: {row['update_frequency']}\n")
            f.write(f"- **Description**: {row['description']}\n\n")
        
        f.write("## How to Use\n")
        f.write("1. Open Power BI Desktop\n")
        f.write("2. Click 'Get Data' → 'Text/CSV'\n")
        f.write("3. Load each dataset\n")
        f.write("4. Create relationships between tables\n")
        f.write("5. Build your dashboard!\n")
    
    print("\n All datasets generated successfully!")
    print(" Check 'powerbi/datasets/' directory for CSV files")

if __name__ == "__main__":
    main()