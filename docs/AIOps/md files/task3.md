🔍 Basic Analysis with PromQL
Module 3: Master the Prometheus Query Language

Transform raw metrics into actionable insights with PromQL

🎯 What You'll Learn
PromQL Fundamentals: Select and filter time-series data
Label Selectors: Filter metrics by dimensions
Rate Calculations: Convert counters to meaningful rates
Aggregation Operators: Combine data with sum(), avg(), max()
CPU Usage Analysis: Calculate resource utilization
Static Thresholds: Understand traditional alerting and its limits


🔍 Step 1: Simple Metric Selection
📝 What to Do
Let's start with the simplest PromQL query: selecting a metric by name. The up metric indicates whether a target is reachable (1 = up, 0 = down).

Click on the Prometheus UI icon on the top right side to open the Expression Browser, then execute this query in the query box:

🚀 Run Query
up
📋 Copy
💡 Expected Result
You should see time series for each target Prometheus is scraping:

up{job="prometheus",instance="prometheus:9090"} = 1
up{job="node-exporter",instance="node-exporter:9100"} = 1
A value of 1 means the target is UP, 0 means DOWN.

🏷️ Step 2: Label Filtering
📝 What to Do
Labels allow you to filter metrics by dimensions. Let's query the up metric but filter it to show only the node-exporter target.

Use the label selector syntax: {label_name="value"}

🚀 Run Query
up{job="node-exporter"}
📋 Copy
💡 Expected Result
You should see only the Node Exporter target:

up{job="node-exporter",instance="node-exporter:9100"} = 1
The Prometheus target is filtered out because its job label is "prometheus", not "node-exporter".

🔍 Label Selector Syntax
label="value" - Exact match
label!="value" - Not equal
label=~"regex" - Regex match
label!~"regex" - Negative regex match

⚡ Step 3: Calculating Rates with rate()
📝 What to Do
The rate() function calculates the per-second average rate of increase for a counter over a specified time range.

Let's calculate the rate at which CPU 0 is spending time in idle mode over the last 5 minutes:

Note: [5m] is a range vector selector that tells Prometheus to look at the last 5 minutes of data.

🚀 Run Query
rate(node_cpu_seconds_total{cpu="0",mode="idle"}[5m])
📋 Copy
💡 Expected Result
You'll see a decimal value like 0.85 or 0.92.

Interpretation: This is the fraction of time (0.0 to 1.0) that CPU 0 is idle. A value of 0.85 means the CPU is idle 85% of the time (and therefore working 15% of the time).

🔍 Why Use rate()?
node_cpu_seconds_total is a counter—it only increases. The raw value (e.g., 123456.78 seconds) tells you total seconds since boot, which isn't useful. The rate() function converts this into a meaningful rate: "How fast is this counter increasing right now?"



📊 Step 4: Aggregation with avg()
📝 What to Do
Aggregation operators like avg(), sum(), and max() combine multiple time series into a single result.

Let's calculate the average idle rate across all CPU cores using avg():

🚀 Run Query
avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))
📋 Copy
💡 Expected Result
You'll see a single value representing the average idle percentage across all CPUs (e.g., 0.88).

What happened: Instead of seeing one time series per CPU core, avg() combined them all into a single average value.

🔍 Common Aggregation Operators
sum() - Add all values together
avg() - Calculate the average
max() - Find the maximum value
min() - Find the minimum value
count() - Count the number of time series


💻 Step 5: Calculate CPU Usage Percentage
📝 What to Do
Now let's calculate something meaningful: CPU usage percentage. We've been querying idle time, but what we really want to know is how much the CPU is working.

The logic: If the CPU is idle 85% of the time (0.85), it's working 15% of the time. We can calculate this as:

CPU Usage = 100% - (Idle % × 100)

🚀 Run Query
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
📋 Copy
💡 Expected Result
You should see a percentage value like 15.8 or 32.4.

Congratulations! You've just calculated the average CPU usage percentage across all cores—a metric that's actually useful for monitoring!

🔍 Query Breakdown
rate(node_cpu_seconds_total{mode="idle"}[5m]) - Calculate idle rate per core
avg(...) - Average across all cores
... * 100 - Convert to percentage
100 - ... - Invert to get usage instead of idle


🔔 Step 6: Static Threshold Alert Query
📝 What to Do
Now that you can calculate CPU usage, let's write a query for a traditional static threshold alert. This is the "old-school" way of monitoring: define a fixed threshold and alert when it's breached.

Example alert rule: "Alert when CPU usage is above 80%"

We'll use a boolean comparison to return 1 (true) if CPU usage exceeds 80%, or nothing if it's below:

🚀 Run Query
(100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 80
📋 Copy
💡 Expected Result
If your CPU usage is below 80%: Empty query result

If your CPU usage is above 80%: You'll see a value (the alert would fire)

Note: Your CPU is likely idle right now, so this query will return no results. That's expected—the alert is not firing because CPU usage is normal.

⚠️ The Static Threshold Problem
This query represents the traditional monitoring approach—but it has serious limitations:

One-size-fits-all: 80% might be normal for some workloads, critical for others
No context: High CPU during a batch job is expected; high CPU on a web server might be a problem
Alert fatigue: Too many false alarms → engineers ignore alerts
Can't adapt: Doesn't learn from historical patterns or seasonal trends


🎯 Step 7: Additional Practice Queries
📝 Practice These Queries
Now that you understand the fundamentals, try these additional queries to solidify your PromQL skills:

1️⃣ Available Memory in GB
node_memory_MemAvailable_bytes / 1024 / 1024 / 1024
📋 Copy
Converts bytes to gigabytes for easier reading

2️⃣ Memory Usage Percentage
100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)
📋 Copy
Calculates the percentage of memory in use

3️⃣ Network Receive Rate (bytes/sec)
rate(node_network_receive_bytes_total[5m])
📋 Copy
Shows how many bytes per second are being received on network interfaces

4️⃣ Disk Space Available (GB)
node_filesystem_avail_bytes{mountpoint="/"} / 1024 / 1024 / 1024
📋 Copy
Shows available disk space on the root filesystem in GB

💡 Pro Tip: Use the Graph Tab
Switch to the Graph tab in Prometheus to see how these metrics change over time. This visualization helps you spot trends, spikes, and patterns that aren't visible in instant values alone!



🎓 Understanding the Bigger Picture
🏗️ Where We Are in the AIOps Journey
You've now learned key skills for the AI-Driven Insights layer of the AIOps pyramid:

     ┌───────────────────────────────┐
     │  3. Intelligent Actions       │  ← (Future)
     ├───────────────────────────────┤
     │  2. AI-Driven Insights        │  ← ✅ YOU ARE HERE!
     │     (PromQL, Analysis Tools)  │     (Module 3)
     ├───────────────────────────────┤
     │  1. High-Quality Data         │  ← ✅ (Module 2)
     └───────────────────────────────┘
⚠️ The Manual Monitoring Challenge
What you've learned in this lab—PromQL queries and static thresholds—is the traditional approach to monitoring. It works, but it has limits:

Manual threshold tuning: You have to decide what "80% CPU" means
Context-blind: Doesn't know if high CPU is expected or problematic
Alert storms: One issue can trigger dozens of alerts
Reactive, not predictive: Alerts fire after problems occur
Human bottleneck: Requires experienced engineers to interpret alerts
🤖 Why AI/ML Changes Everything
In Module 4, you'll see how AI and machine learning overcome these limitations:

Adaptive baselines: Learns what's "normal" for each service and time of day
Context-aware: Understands deployment schedules, traffic patterns, dependencies
Anomaly detection: Flags unusual behavior, not just threshold breaches
Predictive analytics: Forecasts issues before they cause outages
Reduced noise: Fewer false positives, higher signal-to-noise ratio
But AI doesn't replace PromQL—it builds on it. The queries you wrote today will feed the ML models you'll deploy in the next module!

🚀 What's Next
In the next module, you'll:

Module 4: Deploy AI-powered anomaly detection to automatically spot unusual behavior
Learn how machine learning adapts to your metrics and detects anomalies that static thresholds miss
Train ML models using IsolationForest to detect anomalies automatically

🎉 Congratulations!
You've mastered PromQL fundamentals and completed Module 3!

✅ Skills You've Gained
✅ Write PromQL queries to select and filter metrics
✅ Use label selectors to narrow down time series
✅ Calculate rates from counter metrics with rate()
✅ Aggregate data with sum(), avg(), max(), min()
✅ Derive meaningful metrics like CPU usage percentage
✅ Write queries for threshold-based alerts
✅ Understand the limitations of static thresholds
🚀 What You've Accomplished
You can now analyze time-series data like a pro! You understand both the power of PromQL and why manual threshold monitoring isn't enough for modern systems. You're ready to build on this foundation with AI-driven insights.