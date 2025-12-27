# Service Dependencies

## Overview
This document maps service dependencies and data flow in our streaming platform.

## High-Level Architecture

```
┌─────────────────┐
│  Applications   │ (Producers)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Kafka Cluster  │ (Event Stream)
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Consumer│ │Consumer│ │Consumer│ │Consumer│
│Group 1 │ │Group 2 │ │Group 3 │ │Group 4 │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
┌─────────────────────────────────────┐
│         OpenSearch Cluster          │
└─────────────────────────────────────┘
```

## Critical Service Dependencies

### 1. User API Service
**Depends on:**
- Kafka (user-events topic) - **CRITICAL**
- OpenSearch (user-logs index) - Medium
- VictoriaMetrics (metrics push) - Low

**Impact if down:**
- Unable to publish user events → Data loss risk
- Cannot query user activity logs
- Monitoring gaps

**Mitigation:**
- Kafka local buffer (10 minutes)
- Circuit breaker for OpenSearch queries
- Async metrics push

---

### 2. Analytics Pipeline
**Depends on:**
- Kafka (multiple topics) - **CRITICAL**
- OpenSearch (analytics index) - **CRITICAL**
- S3 (data lake) - Medium

**Consumers:**
- `analytics-aggregator` (Kafka → OpenSearch)
- `real-time-stats` (Kafka → Redis)
- `data-warehouse-loader` (Kafka → S3)

**Impact if down:**
- Real-time dashboard stale data (> 5 minutes)
- Analytics queries fail
- Data warehouse delays

---

### 3. Log Aggregation Service
**Depends on:**
- Kafka (logs topic) - **CRITICAL**
- OpenSearch (application-logs) - **CRITICAL**

**Data Flow:**
```
Application Logs → Fluentd → Kafka → Logstash → OpenSearch
```

**Impact if down:**
- Cannot debug production issues
- Alert delays
- Compliance logging gaps

---

### 4. Alerting Service
**Depends on:**
- VictoriaMetrics (metric queries) - **CRITICAL**
- OpenSearch (log-based alerts) - **CRITICAL**
- Kafka (alert-events) - Medium
- PagerDuty API - Medium

**Impact if down:**
- No alerts → Incidents undetected
- On-call not paged
- SLA risk

---

## Dependency Matrix

| Service | Kafka | OpenSearch | VictoriaMetrics | S3 | Redis |
|---------|-------|------------|-----------------|----|----|
| **User API** | CRITICAL | Medium | Low | - | - |
| **Analytics** | CRITICAL | CRITICAL | Medium | Medium | Medium |
| **Logs** | CRITICAL | CRITICAL | - | Low | - |
| **Alerting** | Medium | CRITICAL | CRITICAL | - | - |
| **Reporting** | - | CRITICAL | CRITICAL | CRITICAL | - |
| **Monitoring** | Low | - | CRITICAL | - | - |

**Legend:**
- **CRITICAL**: Service cannot function without it
- **Medium**: Degraded functionality, fallback exists
- **Low**: Optional, metrics/logging only

---

## Failure Scenarios

### Scenario 1: Kafka Cluster Down
**Affected Services:**
- User API (buffered for 10 min, then errors)
- Analytics Pipeline (stopped, lag builds up)
- Log Aggregation (logs buffered in Fluentd)

**Action:**
1. Page on-call immediately
2. Check broker status
3. Restart brokers if needed
4. Monitor consumer lag after recovery

**Recovery Time:** 15-30 minutes

---

### Scenario 2: OpenSearch Cluster Down
**Affected Services:**
- Analytics (queries fail, dashboards down)
- Log search (cannot debug issues)
- Alerting (log-based alerts disabled)

**Action:**
1. Switch to backup cluster (if available)
2. Check cluster health, restart if needed
3. Notify teams via Slack
4. Use CloudWatch Logs as fallback

**Recovery Time:** 30-60 minutes

---

### Scenario 3: VictoriaMetrics Down
**Affected Services:**
- Grafana dashboards (no data)
- Alerting (metric-based alerts disabled)
- Capacity planning (data gaps)

**Action:**
1. Check process status, disk space
2. Restart VictoriaMetrics
3. Verify Prometheus exporters still pushing
4. Use CloudWatch as fallback for AWS resources

**Recovery Time:** 10-20 minutes

---

## Cascading Failure Prevention

### Circuit Breakers
```python
# OpenSearch queries
max_retries: 3
timeout: 5s
fallback: cached_data or error_response

# Kafka producers
retry.backoff.ms: 100
max.in.flight.requests.per.connection: 1
enable.idempotence: true
```

### Rate Limiting
- Kafka producers: 1000 msg/sec per client
- OpenSearch queries: 100 req/sec per service
- VictoriaMetrics: 10K datapoints/sec

### Health Checks
- **Kafka**: Check broker connectivity every 30s
- **OpenSearch**: Cluster health API every 60s
- **VictoriaMetrics**: HTTP /health endpoint every 30s

---

## Data Flow Diagrams

### User Event Processing
```
User Action
    ↓
API Gateway
    ↓
User Service (produces to Kafka)
    ↓
user-events topic (Kafka)
    ↓
    ├─→ Analytics Consumer → OpenSearch (metrics index)
    ├─→ Audit Consumer → OpenSearch (audit-logs index)
    └─→ Real-time Consumer → Redis (cache)
```

### Log Aggregation Flow
```
Application Logs
    ↓
Fluentd Agent (on host)
    ↓
logs topic (Kafka)
    ↓
Logstash Pipeline
    ↓
OpenSearch (application-logs-*)
    ↓
Alerting Rules (check errors, warnings)
```

---

## Cross-Region Dependencies

### Primary Region: us-east-1
- All production services
- Primary Kafka cluster
- Primary OpenSearch clusters

### Secondary Region: us-west-2
- Kafka MirrorMaker (async replication)
- OpenSearch snapshots (S3 cross-region)
- Read-only failover mode

**Failover Time:** ~30 minutes (manual process)

---

## Contact Information

| Service | Team | Slack Channel | On-Call |
|---------|------|---------------|---------|
| Kafka | Platform | #platform-kafka | @platform-oncall |
| OpenSearch | Platform | #platform-search | @platform-oncall |
| VictoriaMetrics | SRE | #sre-monitoring | @sre-oncall |
| Applications | Dev Teams | #dev-support | @dev-oncall |

---

## Update Schedule
- **Last Updated**: 2025-11-01
- **Next Review**: 2025-12-01
- **Owner**: Platform Engineering Team
