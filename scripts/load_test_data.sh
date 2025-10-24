#!/bin/bash

# Load Test Data into VictoriaMetrics
# This script populates VictoriaMetrics with sample metrics data

echo "🚀 Loading test data into VictoriaMetrics..."

# VictoriaMetrics endpoint
VM_URL="${VM_URL:-http://localhost:8428}"
API_ENDPOINT="$VM_URL/api/v1/import/prometheus"

echo "📍 Using VictoriaMetrics at: $VM_URL"
echo ""

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

# CPU Metrics
echo "1️⃣ CPU Metrics..."
send_metric 'cpu_usage{host="server1",environment="production"} 45' "CPU usage server1"
send_metric 'cpu_usage{host="server2",environment="production"} 78' "CPU usage server2"
send_metric 'cpu_usage{host="server3",environment="staging"} 23' "CPU usage server3"
send_metric 'cpu_usage{host="server4",environment="development"} 56' "CPU usage server4"
echo ""

# Memory Metrics
echo "2️⃣ Memory Metrics..."
send_metric 'memory_bytes{host="server1",type="used"} 4294967296' "Memory used server1 (4GB)"
send_metric 'memory_bytes{host="server1",type="total"} 8589934592' "Memory total server1 (8GB)"
send_metric 'memory_bytes{host="server2",type="used"} 6442450944' "Memory used server2 (6GB)"
send_metric 'memory_bytes{host="server2",type="total"} 17179869184' "Memory total server2 (16GB)"
echo ""

# Network Metrics
echo "3️⃣ Network Metrics..."
send_metric 'network_bytes_sent{host="server1",interface="eth0"} 1048576000' "Network sent server1"
send_metric 'network_bytes_received{host="server1",interface="eth0"} 2097152000' "Network received server1"
send_metric 'network_bytes_sent{host="server2",interface="eth0"} 524288000' "Network sent server2"
send_metric 'network_bytes_received{host="server2",interface="eth0"} 3145728000' "Network received server2"
echo ""

# Disk Metrics
echo "4️⃣ Disk Metrics..."
send_metric 'disk_usage_percent{host="server1",mount="/"} 67' "Disk usage server1"
send_metric 'disk_usage_percent{host="server2",mount="/"} 45' "Disk usage server2"
send_metric 'disk_io_reads{host="server1",device="sda"} 123456' "Disk reads server1"
send_metric 'disk_io_writes{host="server1",device="sda"} 234567' "Disk writes server1"
echo ""

# Application Metrics
echo "5️⃣ Application Metrics..."
send_metric 'http_requests_total{service="api",status="200"} 15234' "HTTP 200 responses"
send_metric 'http_requests_total{service="api",status="500"} 12' "HTTP 500 errors"
send_metric 'http_request_duration_seconds{service="api",quantile="0.95"} 0.234' "HTTP 95th percentile latency"
send_metric 'active_connections{service="database"} 45' "Database connections"
echo ""

# Custom Test Metric
echo "6️⃣ Custom Test Metrics..."
send_metric 'test_metric{label="value"} 123' "Test metric"
send_metric 'app_version{service="backend",version="1.2.3"} 1' "App version info"
echo ""

echo "✨ Test data loading complete!"
echo ""
echo "📝 You can now query these metrics in VictoriaMetrics:"
echo "   • cpu_usage"
echo "   • memory_bytes"
echo "   • network_bytes_sent / network_bytes_received"
echo "   • disk_usage_percent / disk_io_reads / disk_io_writes"
echo "   • http_requests_total"
echo "   • active_connections"
echo "   • test_metric"
echo ""
echo "🔍 Try queries like:"
echo "   • cpu_usage{host=\"server1\"}"
echo "   • rate(http_requests_total[5m])"
echo "   • memory_bytes{type=\"used\"} / memory_bytes{type=\"total\"}"
