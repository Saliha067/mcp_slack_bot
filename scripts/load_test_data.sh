#!/bin/bash

# Load Test Data into VictoriaMetrics
# This script populates VictoriaMetrics with sample metrics for infrastructure troubleshooting
# Generates time-series data covering the last 24 hours

echo "🚀 Loading test data into VictoriaMetrics..."

# VictoriaMetrics endpoint
VM_URL="${VM_URL:-http://localhost:8428}"
API_ENDPOINT="$VM_URL/api/v1/import/prometheus"

echo "📍 Using VictoriaMetrics at: $VM_URL"
echo ""

# Get current timestamp and calculate 24 hours ago
NOW=$(date +%s)
HOURS_AGO_24=$((NOW - 86400))

# Function to send metric data
send_metric() {
    local data="$1"
    local description="$2"
    
    echo "📊 Loading: $description"
    curl -s -d "$data" "$API_ENDPOINT" > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Success"
    else
        echo "   ❌ Failed"
    fi
}

# Function to generate time-series data with timestamps
# Usage: generate_timeseries "metric_name{labels}" base_value variation_percent
generate_timeseries() {
    local metric="$1"
    local base_value="$2"
    local variation="${3:-10}"  # Default 10% variation
    
    local data=""
    # Generate data points every 5 minutes for last 24 hours (288 points)
    for i in $(seq 0 5 1440); do
        local timestamp=$((NOW - (i * 60)))
        # Add random variation to base value
        local random_var=$((RANDOM % variation))
        local value=$(awk "BEGIN {print $base_value * (1 + ($random_var - $variation/2) / 100)}")
        data="${data}${metric} ${value} ${timestamp}000\n"
    done
    echo -e "$data"
}

# OpenSearch Metrics
echo "1️⃣ OpenSearch Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'opensearch_jvm_mem_heap_used_percent{cluster="prod-logs",node="node-1"}' 75 15)" "OpenSearch JVM heap node-1"
send_metric "$(generate_timeseries 'opensearch_jvm_mem_heap_used_percent{cluster="prod-logs",node="node-2"}' 82 15)" "OpenSearch JVM heap node-2"
send_metric "$(generate_timeseries 'opensearch_jvm_mem_heap_used_percent{cluster="prod-metrics",node="node-1"}' 45 10)" "OpenSearch metrics cluster heap"
send_metric "$(generate_timeseries 'opensearch_search_query_time_seconds{cluster="prod-logs"}' 0.234 50)" "OpenSearch query latency"
send_metric "$(generate_timeseries 'opensearch_search_query_total{cluster="prod-logs"}' 15420 20)" "OpenSearch query count"
send_metric "$(generate_timeseries 'opensearch_indices_indexing_index_time_seconds{cluster="prod-logs"}' 0.056 30)" "OpenSearch indexing time"
send_metric "$(generate_timeseries 'opensearch_cluster_shards_active{cluster="prod-logs"}' 120 5)" "OpenSearch active shards"
send_metric "$(generate_timeseries 'opensearch_cluster_shards_unassigned{cluster="prod-logs"}' 0 0)" "OpenSearch unassigned shards"
echo ""

# Kafka Metrics
echo "2️⃣ Kafka Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'kafka_consumer_lag{group="analytics-pipeline",topic="user-events",partition="0"}' 1245 40)" "Kafka consumer lag analytics p0"
send_metric "$(generate_timeseries 'kafka_consumer_lag{group="analytics-pipeline",topic="user-events",partition="1"}' 987 40)" "Kafka consumer lag analytics p1"
send_metric "$(generate_timeseries 'kafka_consumer_lag{group="log-aggregation",topic="logs",partition="0"}' 45 20)" "Kafka consumer lag logs"
send_metric "$(generate_timeseries 'kafka_consumer_records_consumed_rate{group="analytics-pipeline"}' 1523.5 25)" "Kafka consumer rate"
send_metric "$(generate_timeseries 'kafka_producer_record_send_rate{client="user-service"}' 2341.2 30)" "Kafka producer rate"
send_metric "$(generate_timeseries 'kafka_server_under_replicated_partitions{broker="1"}' 0 0)" "Kafka under-replicated p1"
send_metric "$(generate_timeseries 'kafka_server_under_replicated_partitions{broker="2"}' 0 0)" "Kafka under-replicated p2"
send_metric "$(generate_timeseries 'kafka_controller_active_count{broker="1"}' 1 0)" "Kafka controller"
send_metric "$(generate_timeseries 'kafka_network_request_total{broker="1",request="Produce"}' 45231 15)" "Kafka produce requests"
send_metric "$(generate_timeseries 'kafka_network_request_total{broker="1",request="Fetch"}' 89432 15)" "Kafka fetch requests"
echo ""

# CPU Metrics
echo "3️⃣ CPU Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'cpu_usage{host="server1",environment="production"}' 45 20)" "CPU usage server1"
send_metric "$(generate_timeseries 'cpu_usage{host="server2",environment="production"}' 78 15)" "CPU usage server2"
send_metric "$(generate_timeseries 'cpu_usage{host="opensearch-node-1",environment="production"}' 65 18)" "CPU usage OpenSearch node1"
send_metric "$(generate_timeseries 'cpu_usage{host="kafka-broker-1",environment="production"}' 72 12)" "CPU usage Kafka broker1"
echo ""

# Memory Metrics
echo "4️⃣ Memory Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'memory_bytes{host="server1",type="used"}' 4294967296 10)" "Memory used server1 (4GB)"
send_metric "$(generate_timeseries 'memory_bytes{host="server1",type="total"}' 8589934592 0)" "Memory total server1 (8GB)"
send_metric "$(generate_timeseries 'memory_bytes{host="opensearch-node-1",type="used"}' 10737418240 15)" "Memory used OpenSearch (10GB)"
send_metric "$(generate_timeseries 'memory_bytes{host="opensearch-node-1",type="total"}' 17179869184 0)" "Memory total OpenSearch (16GB)"
send_metric "$(generate_timeseries 'memory_bytes{host="kafka-broker-1",type="used"}' 8589934592 12)" "Memory used Kafka (8GB)"
send_metric "$(generate_timeseries 'memory_bytes{host="kafka-broker-1",type="total"}' 17179869184 0)" "Memory total Kafka (16GB)"
echo ""

# Network Metrics
echo "5️⃣ Network Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'network_bytes_sent{host="server1",interface="eth0"}' 1048576000 25)" "Network sent server1"
send_metric "$(generate_timeseries 'network_bytes_received{host="server1",interface="eth0"}' 2097152000 25)" "Network received server1"
send_metric "$(generate_timeseries 'network_bytes_sent{host="kafka-broker-1",interface="eth0"}' 524288000 30)" "Network sent Kafka broker"
send_metric "$(generate_timeseries 'network_bytes_received{host="server2",interface="eth0"}' 3145728000 20)" "Network received server2"
echo ""

# Disk Metrics
echo "6️⃣ Disk Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'disk_usage_percent{host="server1",mount="/"}' 67 5)" "Disk usage server1"
send_metric "$(generate_timeseries 'disk_usage_percent{host="server2",mount="/"}' 45 5)" "Disk usage server2"
send_metric "$(generate_timeseries 'disk_io_reads{host="server1",device="sda"}' 123456 20)" "Disk reads server1"
send_metric "$(generate_timeseries 'disk_io_writes{host="server1",device="sda"}' 234567 20)" "Disk writes server1"
echo ""

# Application Metrics
echo "7️⃣ Application Metrics (24h time-series)..."
send_metric "$(generate_timeseries 'http_requests_total{service="api",status="200"}' 15234 30)" "HTTP 200 responses"
send_metric "$(generate_timeseries 'http_requests_total{service="api",status="500"}' 12 50)" "HTTP 500 errors"
send_metric "$(generate_timeseries 'http_request_duration_seconds{service="api",quantile="0.95"}' 0.234 40)" "HTTP 95th percentile latency"
send_metric "$(generate_timeseries 'active_connections{service="database"}' 45 25)" "Database connections"
echo ""

echo "✨ Test data loading complete!"
echo ""
echo "📝 Loaded 24 hours of time-series data for:"
echo "   • OpenSearch metrics (JVM heap, query latency, shards)"
echo "   • Kafka metrics (consumer lag, producer rate, requests)"
echo "   • System metrics (CPU, memory, network, disk)"
echo "   • Application metrics (HTTP requests, latency, connections)"
echo ""
echo "🔍 Try queries like:"
echo "   • opensearch_search_query_time_seconds{cluster=\"prod-logs\"}[1h]"
echo "   • kafka_consumer_lag{group=\"analytics-pipeline\"}[30m]"
echo "   • rate(http_requests_total[5m])"
echo "   • cpu_usage{host=\"server1\"}[2h]"
echo ""
echo "⏰ Time range queries will now work for the last 24 hours!"