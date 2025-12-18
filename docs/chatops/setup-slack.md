Slack App Setup
Step 1: Create a Slack Workspace (if needed)
If you don't already have a Slack workspace:
* Go to https://slack.com/create
* Enter your email and follow the setup wizard
* Create a workspace name (e.g., "chatops-lab")
* Invite yourself or skip inviting others
Step 2: Create a Slack App
* Go to https://api.slack.com/apps
* Click "Create New App"
* Select "From scratch"
* Enter App Name: ChatOps Bot
* Select your workspace
* Click "Create App"
Step 3: Enable Socket Mode
Socket Mode allows your bot to connect without exposing a public webhook URL.
* In your app settings, go to Settings → Socket Mode
* Toggle "Enable Socket Mode" to ON
* When prompted, create an app-level token:
    * Token Name: chatops-token
    * Scope: connections:write
    * Click "Generate"
* Copy the token (starts with xapp-) - this is your SLACK_APP_TOKEN
* Store it safely - you'll need it later
Step 4: Configure OAuth Scopes
* Go to Features → OAuth & Permissions
* Scroll to "Bot Token Scopes"
* Add the following scopes:
    * chat:write - Send messages
    * commands - Enable slash commands
    * app_mentions:read - Respond to mentions
Step 5: Install App to Workspace
* Scroll to the top of OAuth & Permissions page
* Click "Install to Workspace"
* Review permissions and click "Allow"
* Copy the "Bot User OAuth Token" (starts with xoxb-) - this is your SLACK_BOT_TOKEN
* Store it safely
Step 6: Create a Slash Command
* Go to Features → Slash Commands
* Click "Create New Command"
* Fill in the details:
    * Command: /check-status
    * Request URL: Leave blank (Socket Mode doesn't need this)
    * Short Description: Check instance status from Prometheus
    * Usage Hint: <instance_name>
* Click "Save"
Step 7: Enable Event Subscriptions (Optional)
For the bot to respond to @mentions:
* Go to Features → Event Subscriptions
* Toggle "Enable Events" to ON
* Under Subscribe to bot events, add:
    * app_mention - When someone mentions the bot
* Click "Save Changes"
Summary of Tokens
You should now have two tokens:
# App-level token (Socket Mode)
SLACK_APP_TOKEN=xapp-1-A0XXXXXXXXX-1234567890123-abcdef1234567890

# Bot User OAuth Token
SLACK_BOT_TOKEN=xoxb-1234567890123-1234567890123-abcdefghijklmnopqrstuvwx
Security Note: Never commit these tokens to version control. Store them as environment variables.
Verify Setup
In the next tab, we'll use these tokens to connect your Python bot to Slack.
Troubleshooting
* Can't find Socket Mode? Make sure you created the app "From scratch"
* Commands not working? Ensure Socket Mode is enabled
* Bot not responding? Check that you've installed the app to your workspace