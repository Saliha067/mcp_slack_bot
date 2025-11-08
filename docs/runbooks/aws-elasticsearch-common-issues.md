# AWS Elasticsearch/OpenSearch Common Issues

## Overview
Common issues and solutions for AWS-managed Elasticsearch and OpenSearch Service.

## Common Issues

### 1. ClusterBlockException: Index Read-Only

**Symptom:**
```
ClusterBlockException[blocked by: [FORBIDDEN/12/index read-only / allow delete (api)]
```

**Cause:**
- Disk space > 95% on nodes
- AWS automatic read-only protection triggered

**Solution:**
```bash
# 1. Delete old indices or data
DELETE /old-index-*

# 2. Disable read-only block
PUT /_all/_settings
{
  "index.blocks.read_only_allow_delete": null
}

# 3. Monitor disk space
GET /_cat/allocation?v
```

**Prevention:**
- Set up CloudWatch alarms for disk space > 75%
- Implement Index Lifecycle Management (ILM)
- Use automated snapshots and deletion policies

---

### 2. High JVM Memory Pressure

**Symptom:**
- JVMMemoryPressure metric > 85%
- Slow queries
- Cluster instability

**Cause:**
- Large aggregations
- Too many concurrent searches
- Field data cache issues

**Solution:**
```bash
# 1. Clear caches
POST /_cache/clear

# 2. Check field data usage
GET /_nodes/stats/indices/fielddata?human&fields=*

# 3. Reduce field data
PUT /your-index/_settings
{
  "index.queries.cache.enabled": false
}
```

**Prevention:**
- Use doc values instead of field data
- Limit query result size
- Use pagination (search_after)
- Scale up instance type

---

### 3. Circuit Breaker Errors

**Symptom:**
```
[parent] Data too large, data for [<http_request>] would be [xxx] which is larger than the limit of [yyy]
```

**Cause:**
- Query result set too large
- Aggregation on high-cardinality field
- Circuit breaker protection triggered

**Solution:**
```bash
# 1. Add pagination to queries
GET /index/_search
{
  "size": 100,
  "from": 0
}

# 2. Use search_after for deep pagination
GET /index/_search
{
  "size": 100,
  "search_after": [1234567890, "doc_id"],
  "sort": [
    {"timestamp": "asc"},
    {"_id": "asc"}
  ]
}
```

**Prevention:**
- Always use pagination
- Limit aggregation buckets (max_buckets)
- Increase node instance size if needed

---

### 4. Snapshot Failures

**Symptom:**
- Manual or automated snapshots failing
- "SnapshotInProgressException"

**Cause:**
- Previous snapshot still running
- S3 permissions issue
- Repository configuration error

**Solution:**
```bash
# 1. Check snapshot status
GET /_snapshot/_status

# 2. Cancel stuck snapshot
DELETE /_snapshot/repository-name/snapshot-name

# 3. Verify S3 permissions in IAM role

# 4. Re-register repository
PUT /_snapshot/my-repository
{
  "type": "s3",
  "settings": {
    "bucket": "my-snapshot-bucket",
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789012:role/opensearch-snapshot-role"
  }
}
```

---

### 5. Shard Allocation Failures

**Symptom:**
- Unassigned shards
- Cluster status YELLOW or RED
- `_cluster/health` shows unassigned_shards > 0

**Cause:**
- Not enough nodes for replica count
- Disk space issues
- Shard allocation filters

**Solution:**
```bash
# 1. Check allocation explanation
GET /_cluster/allocation/explain

# 2. Reduce replica count temporarily
PUT /index-name/_settings
{
  "number_of_replicas": 1
}

# 3. Retry shard allocation
POST /_cluster/reroute?retry_failed=true

# 4. Check disk space
GET /_cat/allocation?v
```

---

### 6. Blue/Green Deployment Issues

**Symptom:**
- Domain stuck in "Processing" state
- Deployment taking too long (> 30 minutes)

**Cause:**
- Large cluster with many indices
- Shard relocation during upgrade
- Snapshot in progress

**Solution:**
1. **Wait**: Blue/Green deployments can take 30-60 minutes
2. **Check CloudTrail**: Look for errors in AWS console
3. **Contact AWS Support**: If stuck > 2 hours

**Prevention:**
- Schedule maintenance windows
- Reduce shard count before upgrade
- Ensure no snapshots running

---

### 7. High CPU Usage

**Symptom:**
- CPUUtilization metric > 80% sustained
- Slow cluster performance

**Cause:**
- Too many concurrent searches
- Heavy indexing workload
- Complex aggregations
- Insufficient node resources

**Solution:**
```bash
# 1. Check hot threads
GET /_nodes/hot_threads

# 2. Check task management
GET /_tasks?detailed=true&actions=*search*

# 3. Rate limit indexing
# Reduce bulk indexing batch size

# 4. Scale cluster
# Add data nodes or upgrade instance type
```

---

## AWS-Specific Best Practices

### Monitoring Setup
```python
# Essential CloudWatch Metrics to Monitor:
- ClusterStatus.red
- ClusterStatus.yellow  
- FreeStorageSpace
- JVMMemoryPressure
- CPUUtilization
- SearchLatency
- IndexingLatency
- MasterCPUUtilization
```

### Alert Thresholds
- **Critical**: ClusterStatus.red, JVMMemoryPressure > 95%
- **Warning**: FreeStorageSpace < 25%, CPUUtilization > 80%
- **Info**: SearchLatency > 1000ms

### Scaling Recommendations
- **Vertical**: Increase instance type (r6g.large → r6g.xlarge)
- **Horizontal**: Add data nodes (3 → 6)
- **Storage**: Use gp3 instead of gp2 for better IOPS

## Escalation
1. Check AWS Service Health Dashboard
2. Review CloudWatch Logs Insights
3. Contact AWS Support with domain ARN
4. Escalate to Platform Team Lead if business-critical

## Post-Incident
- Review slow query logs
- Optimize index mappings
- Update monitoring thresholds
- Document findings in incident report
