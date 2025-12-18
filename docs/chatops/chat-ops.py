
#!/usr/bin/env python3
"""
ChatOps Slack Bot for Prometheus Monitoring
This bot responds to /check-status commands and queries Prometheus API,
and includes a Flask webhook for Alertmanager alerts.
"""

import os
import requests
import threading
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize Slack app with tokens from environment variables
# SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-...) must be set
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Configuration
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#alerts")

# Initialize Flask for the webhook listener
flask_app = Flask(__name__)


def query_prometheus(instance_name):
    """
    Query Prometheus API to check if an instance is up

    Args:
        instance_name: The instance name to check (e.g., "localhost:9113")

    Returns:
        dict: Status information with 'status' and 'message' keys
    """
    # FIX: Use 'nginx_up' to check Nginx service status, not the generic 'up' metric.
    # The 'instance_name' should be the Exporter's instance: localhost:9113
    query = f'nginx_up{{instance="{instance_name}"}}'

    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") == "success":
            results = data.get("data", {}).get("result", [])

            if not results:
                return {
                    "status": "unknown",
                    "message": f":mag: No data found for instance: `{instance_name}`. Is the name correct?"
                }

            # Value "1" means up, "0" means down
            value = results[0]["value"][1]

            if value == "1":
                return {
                    "status": "up",
                    "message": f":white_check_mark: Instance `{instance_name}` is UP"
                }
            else:
                return {
                    "status": "down",
                    "message": f":x: Instance `{instance_name}` is DOWN"
                }
        else:
            return {
                "status": "error",
                "message": f":warning: Prometheus query failed: {data.get('error', 'Unknown error')}"
            }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f":interrobang: Failed to query Prometheus at {PROMETHEUS_URL}: {str(e)}"
        }

# --- Slack Command Handlers ---

@app.command("/check-status")
def handle_status_command(ack, command, say):
    """
    Handle the /check-status slash command
    FIX: The command is set to /check-status to match the lab instructions.
    """
    # ACKNOWLEDGE IMMEDIATELY (Required within 3 seconds by Slack)
    ack()

    # Extract the instance name from command text (e.g., "localhost:9113")
    instance_name = command.get("text", "").strip()

    if not instance_name:
        # NOTE: Updated usage to reflect the correct instance name (localhost:9113)
        say("Usage: `/check-status <instance_name>`\nExample: `/check-status localhost:9113`")
        return

    # Query Prometheus and send the formatted response back to Slack
    result = query_prometheus(instance_name)
    say(result["message"])


@app.event("app_mention")
def handle_app_mention(event, say):
    """
    Respond when the bot is mentioned
    """
    say(f"Hello <@{event['user']}>! Use `/check-status <instance_name>` to check instance status.")


# --- Webhook Alert Handler ---

def format_alert_message(alert):
    """Formats an alert payload into a simple Slack message."""
    status = alert.get("status").upper()
    emoji = ":skull_and_crossbones:" if status == "FIRING" else ":white_check_mark:"
    
    # Extract labels and annotations
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    
    # Construct the message
    message = (
        f"{emoji} *{status}: {labels.get('alertname')}*\n"
        f"• Instance: `{labels.get('instance')}`\n"
        f"• Job: `{labels.get('job')}`\n"
        f"• Summary: _{annotations.get('summary', 'N/A')}_"
    )
    return message


@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Receives alerts from Alertmanager."""
    data = request.get_json()
    alerts = data.get("alerts", [])
    
    processed_count = 0
    for alert in alerts:
        try:
            formatted_message = format_alert_message(alert)
            # Post the alert message to the designated channel
            app.client.chat_postMessage(channel=SLACK_CHANNEL, text=formatted_message)
            processed_count += 1
        except Exception as e:
            print(f"Error processing alert: {e}")
            
    return jsonify({"status": "success", "alerts_processed": processed_count})


def run_flask():
    """Starts the Flask server for the webhook in a separate thread."""
    print("Webhook server listening on http://0.0.0.0:5000/webhook")
    # Note: Use a specific port and disable debug for nohup/thread running
    flask_app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_APP_TOKEN"):
        print("ERROR: Please set SLACK_BOT_TOKEN and SLACK_APP_TOKEN environment variables.")
        exit(1)

    # Start Flask webhook in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start the Slack bot in the main thread using Socket Mode
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("ChatOps bot with webhook integration is running...")
    handler.start()