🤖 AI-Powered Anomaly Detection in Grafana
Module 4: Deploy Your First Machine Learning Workflow

🎯 What You'll Accomplish
In this lab, you'll train and deploy an IsolationForest machine learning model for anomaly detection on your monitoring infrastructure. You'll move beyond static thresholds ("alert when CPU > 80%") to intelligent, adaptive monitoring that learns what's normal for your systems.

By the end, you'll understand how machine learning transforms monitoring from reactive to proactive—catching issues that traditional thresholds miss.

📚 The AIOps Journey
Remember the AIOps Pyramid from Module 1?

     ┌───────────────────────────────┐
     │  3. Intelligent Actions       │  ← (Future modules)
     ├───────────────────────────────┤
     │  2. AI-Driven Insights        │  ← 🎯 YOU ARE HERE!
     │     (Anomaly Detection)       │     (Module 4)
     ├───────────────────────────────┤
     │  1. High-Quality Data         │  ← ✅ (Modules 2-3)
     └───────────────────────────────┘
You've built the foundation with high-quality metrics (Module 2) and PromQL analysis (Module 3). Now, you'll add the AI layer that makes monitoring truly intelligent.

🚀 Why This Lab Matters
The Problem with Static Thresholds:

📈 CPU spikes during business hours trigger false alerts
🔍 Real issues hide below arbitrary thresholds
⏰ Constant manual tuning as workloads evolve
🚨 Alert fatigue from too much noise
How ML Anomaly Detection Solves This:

🧠 Learns normal behavior including daily/weekly patterns
📊 Detects true anomalies based on statistical deviation
🔄 Adapts continuously as your infrastructure changes
✨ Reduces noise by 80-95% compared to static thresholds


🎯 Task 1: Set up Python Environment & Install ML Packages
📝 What to Do
Before we can train ML models, we need to install python3.12-venv, pip, and the ML libraries. During this installation, Prometheus will collect metrics in the background for later training!

Step 1: Update package repository (Ubuntu 24.04)

apt update
📋
Step 2: Install Python 3.12 venv and pip

apt install -y python3.12-venv python3-pip
📋
Step 3: Navigate to the scripts directory and create a virtual environment

cd /root/monitoring/scripts
📋
python3 -m venv venv
📋
Step 4: Activate the virtual environment

source /root/monitoring/scripts/venv/bin/activate
📋
Step 5: Upgrade pip to latest version

pip install --upgrade pip
📋
Step 6: Install ML packages from requirements.txt (this may take a few minutes)

pip install -r /root/monitoring/scripts/requirements.txt
📋
Step 7: Verify installation

python3 -c "import sklearn, pandas, numpy, prometheus_api_client; print('✅ All packages installed successfully')"
📋
📦 What Each Package Does
scikit-learn (1.3.2):

The ML library containing IsolationForest algorithm for anomaly detection—includes model training, prediction, and evaluation tools

pandas (2.1.3):

Data manipulation library for handling time-series metrics—used to organize, filter, and transform Prometheus data into ML-ready format

numpy (1.26.2):

Numerical computing library—powers the mathematical operations behind ML algorithms (matrix operations, statistics, etc.)

prometheus-api-client (0.5.3):

Python client for querying Prometheus—fetches historical metrics data for model training and real-time data for detection

💡 What You'll Learn
How to set up a complete Python environment from scratch (install Python, create venv, install packages), understand the key libraries for anomaly detection, and prepare your system for production-ready AI monitoring.


🎯 Task 2: Access Grafana and Verify Environment
📝 What to Do
Your monitoring stack (Prometheus + Grafana + Node Exporter) is already running with a pre-built dashboard. Let's verify everything is working correctly.

Step 1: Click on the Grafana UI icon on the top right side to open Grafana

Step 2: Log in with credentials: admin / GrafanaRocks123!

Step 3: Navigate to Dashboards from the left menu

Step 4: Open the "Node Health Monitor" dashboard

Step 5: Verify you can see 4 panels: CPU Usage, Memory Available, Disk Usage, and Network Traffic

🔗 Quick Access
Use the icons on the top right side of the screen to access:

Grafana UI icon - Visualization dashboard (port 3000)
Prometheus UI icon - Metrics database (port 9090)

💡 What You'll Learn
How to access a pre-configured monitoring stack and verify that metrics are being collected from your system.

📊 About Your Pre-Built Dashboard
✨ What's Already Configured
Your lab environment includes a pre-built Node Health Monitor dashboard with 4 essential panels:

1. CPU Usage (%)

100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
2. Memory Available (GB)

node_memory_MemAvailable_bytes / 1024 / 1024 / 1024
3. Disk Usage (%)

(1 - node_filesystem_avail_bytes{fstype=~"ext4|xfs|btrfs"} / node_filesystem_size_bytes{fstype=~"ext4|xfs|btrfs"}) * 100
4. Network Traffic (MB/s)

RX (Receive):

rate(node_network_receive_bytes_total[5m]) / 1024 / 1024
TX (Transmit):

rate(node_network_transmit_bytes_total[5m]) / 1024 / 1024
🎯 Why These Metrics Matter for ML
These four metrics are the golden signals for system health:

CPU Usage: Shows compute resource utilization patterns
Memory: Reveals memory leaks and capacity issues
Disk: Tracks storage consumption trends (filters for real filesystems: ext4, xfs, btrfs)
Network: Indicates traffic patterns and potential DDoS (separate RX/TX rates)
Your ML model will learn the normal behavior patterns for these metrics—including daily cycles, weekly patterns, and seasonal trends.

🚀 What You'll Do Next
Instead of manually setting thresholds for these metrics ("CPU > 80%"), you'll:

Train an IsolationForest ML model on CPU metrics
Let the model learn normal patterns from historical data
Run real-time anomaly detection to catch unusual behavior
Compare ML results vs. static threshold approach
This dashboard provides the visual context for understanding what the ML model is learning!



🔮 How AI Leads to Proactive Observability
🎯 The Shift from Reactive to Proactive
Traditional monitoring is reactive—you set a threshold, wait for it to breach, then respond:

❌ Reactive Monitoring:
   1. Set rule: "Alert if CPU > 80%"
   2. CPU hits 81%
   3. Alert fires
   4. Engineer investigates
   5. Problem already impacting users
AI-powered monitoring is proactive—it detects unusual patterns before they cause outages:

✅ Proactive Monitoring:
   1. ML learns: "CPU normally 20-40% at 3 PM"
   2. CPU suddenly at 65% at 3 PM (below threshold!)
   3. ML flags as anomaly (unusual for this time)
   4. Engineer investigates early
   5. Problem fixed before users affected
🧠 What Makes ML Proactive
1. Pattern Recognition

ML models learn temporal patterns: CPU usage is naturally higher during business hours, lower at night, and drops on weekends. A spike to 70% at 3 AM is anomalous even if 70% at 2 PM is normal.

2. Statistical Deviation

Instead of "is it above X?", ML asks "is this statistically unusual compared to learned behavior?" A sudden 20% increase might be normal during deployment but anomalous at 3 AM.

3. Early Warning Signs

ML detects subtle changes that precede major incidents: gradual memory growth (leak), slowly increasing latency (database degradation), unusual traffic patterns (security threat).

4. Reduced Alert Fatigue

By eliminating false positives (expected high load) and catching true anomalies, teams can focus on real issues instead of tuning thresholds.

📈 Real-World Impact
Industry data shows proactive AI monitoring delivers:

70-90% reduction in Mean Time To Detect (MTTD)
80-95% fewer false positive alerts
50-70% reduction in Mean Time To Resolve (MTTR)
40-60% decrease in unplanned downtime
🎓 What You'll Experience
In the next tasks, you'll train an IsolationForest model that learns to recognize anomalies. You'll see firsthand how it catches issues that static thresholds miss—and ignores "noise" that would trigger false alerts. This is the future of observability!


🎯 Task 3: Train the IsolationForest Model
✅
Perfect Timing!
By completing Tasks 1 & 2 (package installation + dashboard exploration), Prometheus has now collected sufficient metrics—ideal for training! The script will verify data availability and provide guidance if more time is needed.

📝 What to Do
Now, you'll train your first machine learning model for anomaly detection! The training script will fetch CPU metrics from Prometheus and teach the IsolationForest algorithm what "normal" looks like.

Step 1: Run the training script

python3 /root/monitoring/scripts/train_anomaly_model.py
📋
What the script does:

Connects to Prometheus and fetches up to 1 hour of available CPU metrics
Requires minimum 15 samples of historical data
Engineers features: rolling mean, rolling std, rate of change, hour-of-day
Trains IsolationForest model with 10% contamination (expected outlier rate)
Saves trained model to /root/monitoring/anomaly_model.pkl
💡 Tip: If the script says "insufficient data", wait the suggested time or generate some CPU load with stress --cpu 2 --timeout 60s to create varied patterns.

🧠 Understanding the Training Process
Feature Engineering:

The model doesn't just learn from raw CPU values. It learns from engineered features that capture patterns:

rolling_mean: Average CPU over last 5 samples (smooths noise)
rolling_std: Variability in CPU (detects instability)
rate_of_change: How fast CPU is changing (catches spikes)
hour: Time of day (learns daily patterns)
Contamination Parameter (10%):

This tells the model to expect about 10% of data to be anomalous. It's a tuning knob—higher values flag more anomalies, lower values are more conservative.

💡 What You'll Learn
How to train an ML model on real metrics data, the importance of feature engineering for time-series, and how IsolationForest learns what's "normal" without labeled examples.

🎯 Task 4: Run Real-Time Anomaly Detection
📝 What to Do
With your model trained, it's time to put it to work! The detection script will use your trained model to analyze live CPU metrics and flag any anomalous behavior.

Step 1: Run the detection script

python3 /root/monitoring/scripts/detect_anomalies.py
📋
What the script does:

Loads your trained model from disk
Fetches recent CPU metrics (last 10 minutes)
Applies the same feature engineering as during training
Predicts anomalies: -1 = anomaly, 1 = normal
Calculates anomaly scores (lower = more anomalous)
Provides detailed analysis of any detected anomalies
Optional: Continuous Monitoring

The script will ask if you want to run continuous monitoring for a specified duration (e.g., 5 minutes). This lets you see real-time anomaly detection in action!

🔍 Understanding the Output
Detection Summary:

Shows total samples analyzed, how many were normal vs. anomalous, and the percentage breakdown.

Anomaly Details (if any detected):

Timestamp of the anomaly
Actual CPU usage value
Anomaly score (how unusual it is)
Rolling statistics at that time
Rate of change (was it a sudden spike?)
Why Anomalies Occurred:

The script analyzes why each anomaly was flagged: unusually high/low CPU, high volatility (rapid changes), or patterns that differ from learned behavior.

💡 What You'll Learn
How to apply a trained ML model to live data, interpret anomaly scores and predictions, and understand why certain patterns are flagged as anomalous vs. normal.


⚖️ ML Anomaly Detection vs. Static Thresholds
🎯 Comparing the Two Approaches
Now that you've experienced ML-based anomaly detection, let's compare it to the traditional static threshold approach you might be familiar with.

📊 Side-by-Side Comparison
Aspect	Static Thresholds	ML Anomaly Detection
Configuration	Manual threshold setting
(e.g., "CPU > 80%")	Automatic learning from data
(trains on historical patterns)
Adaptation	Static - requires manual updates	Dynamic - adapts to changes
Context Awareness	No time/pattern awareness	Understands daily/weekly cycles
False Positives	High (expected spikes trigger alerts)	Low (80-95% reduction)
Missed Issues	Problems below threshold go undetected	Catches unusual patterns even below threshold
Best Use Cases	Hard limits (disk 95% full, memory exhaustion)	Dynamic metrics (CPU, network, request rates)
✅ When ML Wins
Scenario 1: Business Hours Pattern

Static: CPU hits 75% every day at 2 PM (business hours) → Alerts daily (false positive)
ML: Learns "75% at 2 PM is normal" → No alert

Scenario 2: Subtle Degradation

Static: CPU slowly climbs from 30% to 65% over a week (below 80% threshold) → No alert
ML: Detects "65% is unusual compared to historical 30%" → Alert (caught early!)

Scenario 3: Unusual Overnight Activity

Static: CPU at 60% at 3 AM (below 80% threshold) → No alert
ML: Knows "3 AM CPU is normally 10-15%" → Alert (potential security issue!)

⚠️ When Static Thresholds Win
Hard Resource Limits

Disk at 95% full is always a problem, regardless of patterns. No need for ML here—a simple threshold works perfectly.

Compliance Requirements

Some regulations require fixed thresholds for auditing. "Memory must never exceed X" is a compliance rule, not a pattern-learning problem.

Simplicity & Explainability

Static thresholds are easier to explain to non-technical stakeholders: "We alert when CPU > 80%" is simpler than "We alert on statistical deviations from learned patterns."

🎯 Best Practice: Hybrid Approach
In production, the best strategy combines both:

ML for dynamic metrics: CPU, memory, network traffic, request rates, latency
Static for hard limits: Disk space, file descriptors, connection limits
Layered alerts: Alert if (ML anomaly detected) OR (critical threshold breached)
This gives you intelligent, context-aware monitoring with a safety net for critical resource limits!


🎉 Congratulations!
You've Successfully Deployed AI-Powered Monitoring!

🚀 What You've Accomplished
✅ Accessed and explored a pre-built monitoring dashboard with key system metrics
✅ Trained an IsolationForest ML model on real CPU metrics from Prometheus
✅ Applied feature engineering to capture patterns (rolling stats, rate of change, seasonality)
✅ Ran real-time anomaly detection on live data using your trained model
✅ Interpreted anomaly scores and understood why certain patterns were flagged
✅ Compared ML vs. static threshold approaches and learned when to use each
✅ Understood proactive observability—how AI catches issues before they cause outages
🧠 Skills You've Gained
Technical Skills:

Training ML models (IsolationForest) on time-series metrics
Feature engineering for anomaly detection
Real-time model inference and anomaly scoring
Prometheus API integration for data fetching
Python scripting for ML workflows
Conceptual Understanding:

How IsolationForest isolates anomalies using random partitioning
The importance of feature engineering for pattern recognition
Statistical anomaly detection vs. threshold-based alerting
Proactive vs. reactive monitoring approaches
Trade-offs between ML and traditional monitoring methods
🎯 Real-World Impact
The skills you've developed in this lab are used by industry leaders:

Netflix uses ML anomaly detection to monitor streaming service health across millions of devices
Uber applies time-series ML to detect issues in their ride-sharing platform before customers are affected
AWS CloudWatch offers anomaly detection for resource monitoring across the entire AWS fleet
Companies report 70-90% reduction in MTTD (Mean Time To Detect) and 80-95% fewer false alerts with ML-powered monitoring
📈 The AIOps Journey Continues
You've now completed Module 4 of the AIOps Foundations course:

✅ Module 1: AI in AIOps - Data to Decisions
✅ Module 2: Collecting the Data Fuel  
✅ Module 3: Basic Analysis with PromQL
✅ Module 4: AI-Powered Anomaly Detection ← YOU JUST COMPLETED! 🎉
🔜 Module 5: AI-Driven Forecasting for Proactive Operations
You've built the complete foundation: high-quality data, powerful analysis, and now intelligent AI-driven insights!

🔮 What's Next: AI-Driven Forecasting
In Module 5, you'll learn to predict the future:

📊 Forecast resource needs before you run out
🔮 Predict capacity requirements for upcoming traffic
⏰ Proactive scaling based on ML predictions
💰 Cost optimization by anticipating demand
🎯 SLA protection through predictive alerting
Move from reactive (alerting on issues) to proactive (preventing issues before they happen)!