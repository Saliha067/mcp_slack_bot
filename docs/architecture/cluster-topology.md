# Cluster Topology

## Overview
This document describes the infrastructure topology for our streaming platform.

## Production Environment

### OpenSearch Clusters

#### **prod-opensearch-logs**
- **Purpose**: Application and system logs aggregation
- **Region**: us-east-1
- **Instance Type**: r6g.xlarge.search
- **Node Count**: 6 data nodes + 3 master nodes
- **Storage**: 2TB per node (gp3)
- **Version**: OpenSearch 2.11
- **Endpoint**: `https://prod-opensearch-logs.us-east-1.es.amazonaws.com`

**Indices:**
- `application-logs-*` (7-day retention)
- `system-logs-*` (14-day retention)
- `security-logs-*` (90-day retention)

#### **prod-opensearch-metrics**
- **Purpose**: Application metrics and analytics
- **Region**: us-east-1
- **Instance Type**: r6g.large.search
- **Node Count**: 3 data nodes + 3 master nodes
- **Storage**: 1TB per node (gp3)
- **Version**: OpenSearch 2.11
- **Endpoint**: `https://prod-opensearch-metrics.us-east-1.es.amazonaws.com`

**Indices:**
- `metrics-*` (30-day retention)
- `analytics-*` (90-day retention)

---

### Kafka Clusters

#### **prod-kafka-main**
- **Purpose**: Primary event streaming and data pipeline
- **Type**: Self-hosted on EC2
- **Instance Type**: m5.2xlarge
- **Node Count**: 6 brokers + 3 ZooKeeper nodes
- **Storage**: 4TB per broker (EBS io2, 10,000 IOPS)
- **Version**: Apache Kafka 3.6.0
- **Zookeeper Ensemble**: 3 nodes (t3.medium)

**Broker Endpoints:**
```
kafka-prod-1.internal.example.com:9092
kafka-prod-2.internal.example.com:9092
kafka-prod-3.internal.example.com:9092
kafka-prod-4.internal.example.com:9092
kafka-prod-5.internal.example.com:9092
kafka-prod-6.internal.example.com:9092
```

**Key Topics:**
- `user-events` (12 partitions, replication: 3)
- `transaction-stream` (24 partitions, replication: 3)
- `audit-logs` (6 partitions, replication: 3)
- `real-time-analytics` (12 partitions, replication: 3)

**Consumer Groups:**
- `analytics-pipeline-consumers` (12 instances)
- `log-aggregation-consumers` (6 instances)
- `alerting-consumers` (3 instances)

---

### Monitoring Stack

#### **VictoriaMetrics**
- **Purpose**: Time-series metrics storage
- **Type**: Self-hosted on EC2
- **Instance Type**: r6i.2xlarge
- **Storage**: 10TB (EBS gp3)
- **Retention**: 180 days
- **Endpoint**: `http://victoria-metrics.internal:8428`

**Data Sources:**
- Prometheus exporters (node, JMX, Kafka)
- Application custom metrics
- CloudWatch metric streams

#### **Grafana**
- **Purpose**: Metrics visualization and dashboards
- **Endpoint**: `https://grafana.example.com`
- **Key Dashboards**:
  - Kafka Cluster Overview
  - OpenSearch Performance
  - Application Metrics
  - Infrastructure Health

---

## Development Environment

### **dev-opensearch**
- **Instance Type**: t3.medium.search
- **Node Count**: 1 data node
- **Storage**: 100GB
- **Endpoint**: `https://dev-opensearch.us-east-1.es.amazonaws.com`

### **dev-kafka**
- **Instance Type**: t3.large
- **Node Count**: 3 brokers + 1 ZooKeeper
- **Storage**: 500GB per broker
- **Endpoint**: `kafka-dev.internal.example.com:9092`

---

## Network Architecture

### VPC Configuration
- **VPC CIDR**: 10.0.0.0/16
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
- **Private Subnets**: 10.0.10.0/24, 10.0.11.0/24, 10.0.12.0/24

### Security Groups
- **opensearch-sg**: Allow 443 from application subnets
- **kafka-sg**: Allow 9092, 9093 from consumer subnets
- **monitoring-sg**: Allow 8428, 3000 from internal VPC

### Load Balancers
- **ALB for Grafana**: grafana.example.com
- **NLB for Kafka**: Internal, cross-zone enabled

---

## Disaster Recovery

### Backup Strategy
- **OpenSearch**: Automated snapshots to S3 (hourly)
- **Kafka**: MirrorMaker 2 to secondary region (5-minute lag)
- **VictoriaMetrics**: Daily backups to S3

### RTO/RPO
- **OpenSearch**: RTO 30 minutes, RPO 1 hour
- **Kafka**: RTO 15 minutes, RPO 5 minutes
- **VictoriaMetrics**: RTO 1 hour, RPO 24 hours

---

## Access & Authentication

### OpenSearch
- AWS IAM roles with fine-grained access control
- SAML integration with corporate SSO

### Kafka
- SASL/SCRAM authentication
- ACLs for topic-level permissions

### Monitoring Tools
- SSO via Okta
- RBAC configured per team

---

## Update Schedule
- **Last Updated**: 2025-11-01
- **Next Review**: 2025-12-01
- **Owner**: Platform Engineering Team
