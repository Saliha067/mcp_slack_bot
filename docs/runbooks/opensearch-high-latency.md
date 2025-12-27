# OpenSearch High Latency Troubleshooting Runbook

## Overview
This runbook guides you through troubleshooting high latency issues in OpenSearch/Elasticsearch clusters.

## Symptoms
- Query response time > 1000ms
- Index operations timing out
- Slow dashboard loads
- Application timeouts

## Common Causes
1. High JVM heap usage
2. Insufficient disk I/O
3. Large query result sets
4. Index mapping issues
5. Shard imbalance
6. GC pauses

## Troubleshooting Steps

### 1. Check Cluster Health
```bash
GET /_cluster/health
GET /_cluster/stats
```

**What to look for:**
- Status should be GREEN
- Unassigned shards = 0
- Active shards balanced across nodes

### 2. Check Node Performance
```bash
GET /_nodes/stats
GET /_cat/nodes?v&h=heap.percent,ram.percent,cpu,load_1m,load_5m
```

**Red flags:**
- Heap usage > 85%
- CPU > 80% sustained
- Load average > number of cores

### 3. Check Index Performance
```bash
GET /_cat/indices?v&s=store.size:desc
GET /_stats/indexing,search
```

**Look for:**
- Very large indices (> 50GB per shard)
- High query rejection rate
- Slow queries

### 4. Check JVM and GC
```bash
GET /_nodes/stats/jvm
```

**Red flags:**
- Old generation > 75%
- GC time increasing
- GC collections > 1 per minute

### 5. Check Recent Slow Queries
```bash
GET /_nodes/hot_threads
GET /_tasks?detailed=true&actions=*search*
```

## Quick Fixes

### High Heap Usage
1. Increase JVM heap (max 32GB)
2. Clear field data cache: `POST /_cache/clear?fielddata=true`
3. Reduce query result size with pagination

### Disk I/O Issues
1. Check disk space: `GET /_cat/allocation?v`
2. Move indices to faster storage
3. Reduce refresh interval temporarily

### Shard Imbalance
1. Reroute shards: `POST /_cluster/reroute`
2. Balance allocation: `PUT /_cluster/settings` with `cluster.routing.rebalance.enable: all`

### GC Pauses
1. Tune GC settings (-XX:+UseG1GC recommended)
2. Increase heap if < 50% of RAM
3. Reduce field data usage

## Escalation Path
1. **First**: Restart affected node (if single node issue)
2. **If cluster-wide**: Check monitoring for recent changes
3. **If unresolved**: Contact Platform Team Lead
4. **Critical**: Page on-call SRE

## Related Metrics to Check
- `opensearch.cluster.health.status`
- `opensearch.jvm.mem.heap_used_percent`
- `opensearch.thread_pool.search.rejected`
- `opensearch.indices.search.query_time_in_millis`

## Post-Incident
- Document root cause
- Update index mapping if needed
- Review query patterns
- Consider index lifecycle policies
