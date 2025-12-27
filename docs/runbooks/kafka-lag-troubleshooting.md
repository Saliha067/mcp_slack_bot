# Kafka Consumer Lag Troubleshooting Runbook

## Overview
Guide for diagnosing and resolving Kafka consumer lag issues in self-hosted Kafka clusters.

## Symptoms
- Consumer lag increasing over time
- Messages not being processed
- Real-time pipelines delayed
- Alert: "Consumer lag > threshold"

## Common Causes
1. Consumer slower than producer rate
2. Consumer process crashes/restarts
3. Rebalancing events
4. Network issues
5. Downstream service bottleneck
6. GC pauses in consumer application

## Troubleshooting Steps

### 1. Check Current Lag
```bash
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group <consumer-group> --describe

# Or using kafka-manager/AKHQ UI
```

**What to check:**
- LAG column per partition
- CURRENT-OFFSET vs LOG-END-OFFSET
- Consumer state (Stable/Rebalancing)

### 2. Check Producer Rate
```bash
kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic <topic-name> \
  --time -1
```

**Calculate:**
- Messages/sec = (current offset - old offset) / time difference
- Compare with consumer processing rate

### 3. Check Consumer Health
```bash
# Check if consumers are active
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group <consumer-group> --state

# Check consumer application logs
tail -f /var/log/consumer-app.log
```

**Red flags:**
- No active consumers
- Frequent rebalancing
- Errors in application logs
- OOM or GC errors

### 4. Check Broker Health
```bash
# Check broker metrics
kafka-broker-api-versions --bootstrap-server localhost:9092

# Check disk usage on broker nodes
df -h /var/kafka-logs
```

**Monitor:**
- Under-replicated partitions
- Offline partitions
- Broker CPU/memory usage

### 5. Check Network Latency
```bash
# From consumer host to broker
ping kafka-broker-1.example.com
traceroute kafka-broker-1.example.com
```

## Quick Fixes

### Consumer Too Slow
1. **Increase consumer instances**: Scale out consumer group
2. **Increase fetch size**: Adjust `max.poll.records` and `fetch.min.bytes`
3. **Optimize consumer logic**: Profile application code
4. **Increase partition count**: More parallelism

### Rebalancing Issues
1. **Increase session timeout**: `session.timeout.ms` (default 10s → 30s)
2. **Increase poll interval**: `max.poll.interval.ms` (default 5min → 10min)
3. **Fix consumer processing time**: Don't block in poll loop

### Broker Issues
1. **Increase replica fetch threads**: `num.replica.fetchers`
2. **Check disk I/O**: Use iostat, move to faster disks
3. **Restart problematic broker**: If specific broker is slow

### Network Issues
1. **Check security groups/firewall**: Ensure broker ports accessible
2. **Increase socket buffer**: `socket.receive.buffer.bytes`
3. **Check DNS resolution**: Verify broker hostnames resolve

## Prevention

### Consumer Configuration
```properties
# Recommended settings
fetch.min.bytes=1048576
fetch.max.wait.ms=500
max.poll.records=500
session.timeout.ms=30000
max.poll.interval.ms=600000
enable.auto.commit=false  # Manual commit for reliability
```

### Monitoring Alerts
- Alert if lag > 10,000 messages
- Alert if lag increasing rate > 1000 msg/min
- Alert if no active consumers
- Alert if rebalancing > 3 times in 10 minutes

## Escalation Path
1. **First**: Scale consumer instances if lag < 1 hour
2. **If lag > 1 hour**: Check for consumer application errors
3. **If broker issue**: Restart affected broker
4. **Critical**: Page Platform Team Lead if data loss risk

## Related Metrics
- `kafka_consumer_lag`
- `kafka_consumer_records_consumed_rate`
- `kafka_producer_record_send_rate`
- `kafka_server_under_replicated_partitions`

## Post-Incident
- Review consumer processing time
- Consider adding consumer instances
- Update consumer configuration
- Document root cause
