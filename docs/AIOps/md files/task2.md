🚀 Welcome to Module 2: Collecting the Data Fuel
🎯 What You'll Learn
In this lab, you'll master the foundation of observability: configuring Prometheus to collect metrics. You'll learn the pull-based scrape model, edit configuration files, deploy a Node Exporter for system metrics, and verify that data is flowing correctly into your time-series database.

📚 Lab Journey
Understand the Prometheus pull model and exposition format
Edit prometheus.yml to define scrape targets
Deploy Prometheus and Node Exporter with Docker Compose
Verify targets are UP and metrics are flowing
Query collected metrics using the Prometheus expression browser
💡 Key Concepts
This lab builds the data foundation for AIOps. Without reliable metrics collection, AI models have nothing to analyze. You're learning the critical first step that enables all intelligent operations.

🔄 Understanding the Prometheus Pull Model
How Prometheus Collects Metrics
Unlike traditional monitoring systems where agents push data to a central server, Prometheus uses a pull-based model. This means Prometheus actively scrapes (fetches) metrics from targets on a regular schedule.

The Pull Model Workflow
Targets expose HTTP endpoints (e.g., http://target:9090/metrics)
Prometheus scrapes these endpoints every scrape_interval (e.g., 15 seconds)
Metrics are parsed and stored in Prometheus's time-series database
Health checks track whether each target is UP or DOWN
✅ Advantages of the Pull Model
Prometheus controls timing - No "thundering herd" of agents reporting simultaneously
Service discovery - Prometheus can automatically find new targets as infrastructure scales
Simpler targets - Just expose an HTTP endpoint, no complex client libraries needed
Centralized configuration - All scrape settings in one place (prometheus.yml)
Network resilience - Prometheus retries failed scrapes automatically


🚀 Step 1: Deploy the Monitoring Stack
📝 What to Do
Launch Prometheus and Node Exporter using Docker Compose. This will start both containers in the background, ready for configuration.

Note: The initial configuration file is a template with TODOs. You'll add scrape targets in the next steps, but let's start the services first to verify they're working.

🚀 Run Command
cd /root && docker compose up -d
📋
📊 Expected Outcome
You should see messages indicating:

Network root_monitoring created
Container prometheus started
Container node-exporter started
Verify: Run docker compose ps to confirm both containers are in "Up" state.




Check if Prometheus and Node Exporter containers are running


✏️ Step 2: Configure Prometheus Self-Monitoring
📝 What to Do
Edit /root/prometheus/prometheus.yml to add a scrape job that monitors Prometheus itself.

Prometheus exposes metrics about its own operation (scrape counts, storage usage, HTTP requests, etc.). This is called self-monitoring and is a best practice.

📄 Configuration to Add
Open the configuration file with vi editor:

vi /root/prometheus/prometheus.yml
📋
Find the scrape_configs: section and add this job:

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets:
          - 'prometheus:9090'
⚠️ Important: Use 2 spaces for indentation (not tabs!). YAML is indentation-sensitive.

🔄 Reload Configuration
After saving the file, reload Prometheus to apply the changes:

docker compose restart prometheus
📋
This restarts the Prometheus container to apply the new configuration.

🔍 Step 3: Verify Prometheus Target is UP
📝 What to Do
Check that Prometheus is successfully scraping its own metrics by verifying the target health in the Prometheus UI.

Open Status → Targets in the Prometheus web interface. You should see the prometheus job with state UP.

🔍 Verification Commands
Test the Prometheus metrics endpoint directly:

curl -s http://localhost:9090/metrics | head -n 20
📋
Check for configuration errors in logs:

docker compose logs prometheus | tail -n 20
📋
📊 Expected Outcome
In the Prometheus UI (Status → Targets), you should see:

Job: prometheus
Endpoint: http://prometheus:9090/metrics
State: UP
Labels: instance="prometheus:9090", job="prometheus"



Verify Prometheus is successfully scraping itself

✏️ Step 4: Configure Node Exporter Scrape Job
📝 What to Do
Add a second scrape job to collect system metrics from the Node Exporter container.

Node Exporter exposes hundreds of metrics about CPU, memory, disk I/O, network, and filesystem usage. These are essential for monitoring the health of your infrastructure.

📄 Configuration to Add
Open the configuration file with vi editor:

vi /root/prometheus/prometheus.yml
📋
Add a second job after the Prometheus job:

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets:
          - 'prometheus:9090'

  - job_name: 'node-exporter'
    static_configs:
      - targets:
          - 'node-exporter:9100'
⚠️ Important: The second job must be at the same indentation level as the first (both start with - job_name).

🔄 Reload Configuration
Save the file and reload Prometheus:

docker compose restart prometheus
📋



Check if prometheus.yml contains node-exporter scrape job configuration

🔍 Step 5: Verify Node Exporter Target is UP
📝 What to Do
Verify that Prometheus is successfully scraping Node Exporter by checking the Targets page.

You should now see two jobs in the Targets page: prometheus and node-exporter, both with state UP.

🔍 Verification Commands
View Node Exporter metrics directly:

curl -s http://localhost:9100/metrics | head -n 30
📋
Count how many metrics Node Exporter exposes:

curl -s http://localhost:9100/metrics | grep '^node_' | wc -l
📋
You'll see hundreds of system metrics!

📊 Expected Outcome
In the Prometheus UI (Status → Targets), you should now see two jobs:

1. prometheus job

Endpoint: http://prometheus:9090/metrics
State: UP
2. node-exporter job

Endpoint: http://node-exporter:9100/metrics
State: UP



Verify both targets are successfully being scraped

📊 Step 6: Query Metrics in the Expression Browser
📝 What to Do
Now that metrics are flowing into Prometheus, explore the data using the expression browser.

The expression browser lets you query metrics using PromQL (Prometheus Query Language). You'll learn PromQL in depth in Module 3, but let's try some basic queries now.

🔍 Queries to Try
Open the Prometheus UI and go to the Graph tab. Try these queries:

1. Check Node Exporter target status

up{job="node-exporter"}
Shows whether the Node Exporter target is up (1) or down (0).

2. CPU usage per mode

node_cpu_seconds_total
Shows CPU time spent in each mode (idle, user, system) per core.

3. Available memory

node_memory_MemAvailable_bytes
Shows available memory in bytes.

4. Network bytes received

node_network_receive_bytes_total
Shows network bytes received per interface.

💡 Tips
Use the Graph tab to visualize metrics over time
Use the Table view to see all time series and labels
Notice the job and instance labels on every metric
Click on a metric in the autocomplete to see its HELP text


🎉 Congratulations! Lab Complete!
✅ What You've Accomplished
Learned the Prometheus pull-based model and why it's advantageous
Understood the Prometheus exposition format (text-based metrics)
Edited prometheus.yml to define scrape jobs
Configured Prometheus self-monitoring (port 9090)
Configured Node Exporter for system metrics (port 9100)
Verified both targets are UP and scraping successfully
Queried metrics using the Prometheus expression browser
Built the data foundation for AIOps!
🎯 Key Takeaways
1. Pull Model Advantage: Prometheus controls scrape timing, enabling service discovery and centralized configuration.

2. Configuration is Key: The prometheus.yml file defines what to monitor and how often.

3. Labels Add Context: Every metric gets job and instance labels for filtering and aggregation.

4. Exporters Extend Reach: Node Exporter is just one of hundreds of exporters available for different systems.

5. Data Enables Intelligence: Everything you've learned builds the foundation for AI-driven operations.

🚀 What's Next: Module 3
In Module 3: Querying with PromQL, you'll master Prometheus Query Language to:

Calculate rates from counters (e.g., requests per second)
Aggregate data across multiple instances
Use functions for statistical analysis
Write queries for alerting rules (Module 4)

