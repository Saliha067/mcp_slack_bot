# Incident Response Checklist

## Overview
Standard operating procedure for handling production incidents.

---

## Severity Levels

### SEV 1 - Critical
- Complete service outage
- Data loss occurring
- Security breach
- Customer-facing impact

**Response Time:** Immediate (< 5 minutes)
**Escalation:** Page on-call immediately

### SEV 2 - High
- Partial service degradation
- Non-critical service down
- Performance severely degraded
- Some customers affected

**Response Time:** < 15 minutes
**Escalation:** Notify on-call, start war room

### SEV 3 - Medium
- Minor degradation
- Single component issue
- Internal tools affected
- No immediate customer impact

**Response Time:** < 1 hour
**Escalation:** Post in team channel

### SEV 4 - Low
- Monitoring alerts
- Minor bugs
- Non-urgent issues

**Response Time:** During business hours
**Escalation:** Create ticket

---

## Incident Response Workflow

### Step 1: Detection & Alert (0-2 minutes)
- [ ] Alert received (PagerDuty, monitoring, user report)
- [ ] Acknowledge alert in PagerDuty
- [ ] Check severity in monitoring dashboard
- [ ] Verify issue is real (not false positive)

**Quick Commands:**
```bash
# Check overall system health
curl https://healthcheck.example.com/status

# Check Kafka cluster
kafka-broker-api-versions --bootstrap-server prod-kafka-1:9092

# Check OpenSearch cluster
curl https://prod-opensearch/_cluster/health
```

---

### Step 2: Communication (2-5 minutes)
- [ ] Create Slack incident thread in `#incidents`
- [ ] Post incident template:

```
🚨 **INCIDENT DECLARED** 🚨
Severity: [SEV 1/2/3/4]
Service: [Kafka/OpenSearch/Analytics/etc]
Impact: [Brief description]
Started: [Timestamp]
Incident Commander: [@your-name]
```

- [ ] Notify relevant teams via @platform-oncall, @sre-oncall
- [ ] Update status page (if customer-facing)
- [ ] For SEV 1/2: Start war room (Zoom link in Slack)

---

### Step 3: Triage & Investigation (5-15 minutes)
- [ ] Gather initial data:
  - Check monitoring dashboards (Grafana)
  - Query relevant logs in OpenSearch
  - Check recent deployments/changes
  - Review VictoriaMetrics for anomalies

**Key Questions:**
1. What broke? (service, cluster, node)
2. When did it break? (exact timestamp)
3. What changed recently? (deployment, config, traffic spike)
4. Is it isolated or widespread?

**Use the bot:**
```
@bot check opensearch prod cluster health
@bot check kafka consumer lag for analytics-pipeline
@bot query victoriametrics for cpu usage last 30 minutes
```

---

### Step 4: Identify Root Cause (15-30 minutes)
- [ ] Follow relevant runbook:
  - [OpenSearch High Latency](../runbooks/opensearch-high-latency.md)
  - [Kafka Consumer Lag](../runbooks/kafka-lag-troubleshooting.md)
  - [AWS Elasticsearch Issues](../runbooks/aws-elasticsearch-common-issues.md)

- [ ] Check service dependencies:
  - [Service Dependencies](../architecture/service-dependencies.md)
  - Identify cascading failures

- [ ] Review recent changes:
  ```bash
  # Check recent deployments
  kubectl get deployments -n production --sort-by=.metadata.creationTimestamp
  
  # Check CloudTrail for AWS changes
  aws cloudtrail lookup-events --start-time 2023-11-01T00:00:00Z
  ```

---

### Step 5: Implement Fix (Variable)
- [ ] Discuss fix with team in war room
- [ ] Document plan in incident thread
- [ ] Execute fix:
  - Restart service
  - Rollback deployment
  - Scale resources
  - Apply configuration change
  - Failover to backup

- [ ] Verify fix is working:
  ```bash
  # Monitor metrics
  watch -n 5 'curl -s https://opensearch/_cluster/health | jq'
  
  # Check consumer lag decreasing
  kafka-consumer-groups --describe --group analytics-pipeline
  ```

- [ ] Update incident thread with progress

**Critical Actions Log:**
```
[14:23] Restarted opensearch-node-3
[14:25] Shard reallocation started
[14:28] Cluster status: YELLOW → GREEN
[14:30] Query latency back to normal (<100ms)
```

---

### Step 6: Monitor & Verify (30-60 minutes)
- [ ] Monitor key metrics for 30 minutes:
  - Error rates
  - Latency (p50, p95, p99)
  - Throughput
  - Resource utilization

- [ ] Check for secondary issues
- [ ] Verify all alerts cleared
- [ ] Confirm customer impact resolved

---

### Step 7: Incident Closure (60-90 minutes)
- [ ] Post resolution update in `#incidents`:

```
✅ **INCIDENT RESOLVED** ✅
Severity: SEV 2
Service: OpenSearch prod-logs cluster
Root Cause: Node 3 disk space 98%, triggered read-only mode
Fix: Deleted old indices, rerouted shards, cleared read-only block
Duration: 1 hour 15 minutes
Impact: Log queries failed for 45 minutes

Post-mortem: [Link to document]
```

- [ ] Update status page (resolved)
- [ ] Close PagerDuty incident
- [ ] Thank responders in thread

---

### Step 8: Post-Incident Review (Next Day)
- [ ] Schedule post-mortem meeting (within 48 hours)
- [ ] Create post-mortem document with:
  - Timeline of events
  - Root cause analysis
  - Impact assessment (users affected, revenue impact, SLA breach)
  - What went well
  - What went poorly
  - Action items (with owners & due dates)

- [ ] Update runbooks if needed
- [ ] Implement preventive measures
- [ ] Share learnings with broader team

**Post-Mortem Template:** [Link to template]

---

## Escalation Matrix

| Severity | Notify | Response Time | Escalate After |
|----------|--------|---------------|----------------|
| SEV 1 | On-call + Manager | Immediate | 15 minutes |
| SEV 2 | On-call + Team | 15 minutes | 1 hour |
| SEV 3 | Team channel | 1 hour | 4 hours |
| SEV 4 | Ticket | Next business day | N/A |

---

## Common Commands Cheat Sheet

### Kafka
```bash
# Consumer lag
kafka-consumer-groups --bootstrap-server kafka-prod-1:9092 --group GROUP_NAME --describe

# Topic info
kafka-topics --bootstrap-server kafka-prod-1:9092 --topic TOPIC_NAME --describe

# Producer test
kafka-console-producer --bootstrap-server kafka-prod-1:9092 --topic test
```

### OpenSearch
```bash
# Cluster health
curl https://opensearch/_cluster/health?pretty

# Node stats
curl https://opensearch/_nodes/stats?pretty

# Clear read-only
curl -X PUT "https://opensearch/_all/_settings" -H 'Content-Type: application/json' -d'
{
  "index.blocks.read_only_allow_delete": null
}
'
```

### VictoriaMetrics
```bash
# Query metrics
curl 'http://victoria-metrics:8428/api/v1/query?query=up'

# Check storage size
curl 'http://victoria-metrics:8428/api/v1/status/tsdb'
```

---

## War Room Etiquette

1. **Stay focused**: Keep discussion technical and solution-oriented
2. **Assign roles**:
   - Incident Commander (coordinates)
   - Investigators (diagnose issue)
   - Communicators (update stakeholders)
   - Scribe (document timeline)
3. **Use thread**: Keep main channel clean, use thread for details
4. **No blame**: Blameless post-mortems, focus on systems not people
5. **Declare victory early**: If fixed, monitor and close, don't over-analyze during incident

---

## Contact Information

| Role | Slack Handle | Phone | PagerDuty |
|------|--------------|-------|-----------|
| Platform On-Call | @platform-oncall | +1-XXX-XXX-XXXX | [Schedule](link) |
| SRE On-Call | @sre-oncall | +1-XXX-XXX-XXXX | [Schedule](link) |
| Engineering Manager | @eng-manager | +1-XXX-XXX-XXXX | - |
| VP Engineering | @vp-eng | +1-XXX-XXX-XXXX | - |

**Incident Channel:** `#incidents`
**War Room Zoom:** https://zoom.us/j/warroom

---

## Update Schedule
- **Last Updated**: 2025-11-01
- **Next Review**: Quarterly
- **Owner**: Platform Team + SRE Team
