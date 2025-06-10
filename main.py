from slack_bolt import App
import re
import csv
import os
from datetime import datetime
import pandas as pd
import send_email
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
import threading
import io  # Added for in-memory file handling

# Get environment variables
def get_env(key, default=None):
    return os.environ.get(key, default)

# Initialize Slack app with bot token
app = App(token=get_env("SLACK_BOT_TOKEN"))
slack_client = WebClient(token=get_env("SLACK_BOT_TOKEN"))

# Define conversation states
STATES = {
    "IDLE": 0,
    "NAME": 1,
    "REASON": 3,
    "AMOUNT": 4,
    "ACCOUNT_NUM": 5,
    "ACCOUNT_NAME": 6,
    "BANK_NAME": 7,
    "CONFIRM": 8,
    "CHOICE": 9,
}

# Store user conversation states
user_states = {}
user_data = {}

def get_user_state(user_id):
    """Get the current state for a user"""
    return user_states.get(user_id, STATES["IDLE"])

def set_user_state(user_id, state):
    """Set the state for a user"""
    user_states[user_id] = state

def get_user_data(user_id):
    """Get the data dictionary for a user"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def clear_user_data(user_id):
    """Clear user data after form completion"""
    if user_id in user_data:
        del user_data[user_id]
    if user_id in user_states:
        del user_states[user_id]

# Add URL verification handler
@app.event("url_verification")
def handle_url_verification(body, ack):
    """Handle Slack URL verification challenge"""
    ack(body["challenge"])

# Handle home tab opening
@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        # Publish view to Home tab
        result = client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Welcome to the Payment Bot!* 🤖\n\nHere are the available commands:"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "• `/start` - Get a greeting message\n• `/form` - Begin the payment application process\n• `/cancel` - Cancel the current operation"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*How to use:*\n1. Type `/form` to start a new payment application\n2. Answer each question as prompted\n3. Confirm your details at the end"
                        }
                    }
                ]
            }
        )
        logger.info(f"Home tab updated for user {event['user']}")
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        # Additional debug info
        if hasattr(e, 'response'):
            logger.error(f"Error response: {e.response}")

# Slash command handlers
@app.command("/start")
def handle_start_command(ack, say, command):
    ack()
    user_id = command["user_id"]
    say(f"Hello <@{user_id}>, Welcome to the payment bot! 👋\nPlease type `/form` to begin the application process.")

@app.command("/form")
def handle_form_command(ack, say, command):
    ack()
    user_id = command["user_id"]
    
    if check_user_submission(user_id):
        set_user_state(user_id, STATES["CHOICE"])
        say ("You've submitted a form before. Reply with: \n- 'Full' to fill out a new form \n- 'Update to change the reason and amount requested")
    else:
        set_user_state(user_id, STATES["NAME"])
        say("Please enter your name:")

@app.command("/cancel")
def handle_cancel_command(ack, say, command):
    ack()
    user_id = command["user_id"]
    clear_user_data(user_id)
    say("Application canceled. Use `/form` to fill the form again.")

def check_user_submission(user_id):
    """Always return False - skip checking previous submissions"""
    return False
    
def get_last_submission(user_id):
    """Return None - skip retrieving previous submissions"""
    return None

@app.message("")
def handle_message(message, say):
    """Handle messages in both DMs and channels where bot is mentioned"""
    user_id = message["user"]
    text = message["text"]
    channel_type = message.get("channel_type", "")
    
    # Skip if message is from bot itself
    if message.get("bot_id"):
        return
    
    # Debug logging - remove after testing
    print(f"Message received from user {user_id}: '{text}'")
    print(f"Channel type: {channel_type}")
    print(f"Current state: {get_user_state(user_id)}")
    
    # Handle both DMs (im) and mentions in channels
    if channel_type == "im" or f"<@{app.client.auth_test()['user_id']}>" in text:
        # Remove bot mention from text if present
        if f"<@{app.client.auth_test()['user_id']}>" in text:
            text = text.replace(f"<@{app.client.auth_test()['user_id']}>", "").strip()
    
        state = get_user_state(user_id)
        data = get_user_data(user_id)
        
        # Process based on current state
        if state == STATES["CHOICE"]:
            user_reply = text.lower()
            if user_reply == "full":
                set_user_state(user_id, STATES["NAME"])
                say("Please enter your name:")
            elif user_reply == "update":
                last_submission = get_last_submission(user_id)
                if last_submission:
                    data["name"] = last_submission["Name"]
                    data["accountnumber"] = last_submission["Account Number"]
                    data["accountname"] = last_submission["Account Name"]
                    data["bank_name"] = last_submission["Bank Name"]
                    set_user_state(user_id, STATES["REASON"])
                    say("Please enter your new reason for payment:")
                else:
                    say("Couldn't find your previous data. Please fill out the full form.")
                    set_user_state(user_id, STATES["NAME"])
                    say("Please enter your name:")
            else:
                say("Invalid choice. Reply with 'Full' or 'Update'.")
        
        elif state == STATES["NAME"]:
            data["name"] = text
            set_user_state(user_id, STATES["REASON"])
            say("Please enter your reason for payment:")
            print(f"User {user_id} moved to REASON state with name: {text}")  # Debug log
            
        elif state == STATES["REASON"]:
            data["reason"] = text
            set_user_state(user_id, STATES["AMOUNT"])
            say("Please enter the payment amount:")
            
        elif state == STATES["AMOUNT"]:
            data["amount"] = text
            set_user_state(user_id, STATES["ACCOUNT_NUM"])
            say("Please enter account number:")
            
        elif state == STATES["ACCOUNT_NUM"]:
            data["accountnumber"] = text
            set_user_state(user_id, STATES["ACCOUNT_NAME"])
            say("Please enter your account name:")
            
        elif state == STATES["ACCOUNT_NAME"]:
            data["accountname"] = text
            set_user_state(user_id, STATES["BANK_NAME"])
            say("Please enter your bank name:")
            
        elif state == STATES["BANK_NAME"]:
            data["bank_name"] = text
            set_user_state(user_id, STATES["CONFIRM"])
            
            # Show confirmation message
            confirmation_message = f"""Please confirm your application details:

*Name:* {data['name']}
*Reason:* {data['reason']}
*Amount:* ₦{data['amount']}
*Account Number:* {data['accountnumber']}
*Account Name:* {data['accountname']}
*Bank Name:* {data['bank_name']}

Review the details and reply with 'Yes' to confirm or 'No' to cancel."""
            
            say(confirmation_message)
            
        elif state == STATES["CONFIRM"]:
            user_reply = text.lower()
            
            if user_reply == "yes":
                # Save to in-memory storage and send files
                save_result = save_user_data(data, user_id)
                
                if save_result["success"]:
                    if save_result["email_sent"] and save_result["file_uploaded"]:
                        say("Your application has been submitted successfully, the accountant has been notified, and the payment data has been sent to their channel. ✅")
                    elif save_result["email_sent"]:
                        say("Your application was saved and the accountant was notified via email, but there was an error sending the file to their channel. Please contact support.")
                    elif save_result["file_uploaded"]:
                        say("Your application was saved and the payment data was sent to the accountant's channel, but there was an error notifying them via email. Please contact support.")
                    else:
                        say("Your application was saved, but there was an error notifying the accountant and sending the file. Please contact support.")
                else:
                    say("An error occurred while saving your data. Please try again.")
                
                clear_user_data(user_id)
                
            elif user_reply == "no":
                clear_user_data(user_id)
                say("Application canceled. Use `/form` to fill the form again.")
                
            else:
                say("Invalid response. Please reply with 'Yes' or 'No'.")
        
        else:
            # User is in IDLE state
            say("Hi! Use `/form` to start a payment application or `/start` for more information.")

def save_user_data(data, user_id):
    """Send user data directly via email without saving"""
    
    # Prepare the user data with timestamp and user_id
    user_data_with_timestamp = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "User ID": user_id,
        "Name": data["name"],
        "Reason": data["reason"],
        "Amount": data["amount"],
        "Account Number": data["accountnumber"],
        "Account Name": data["accountname"],
        "Bank Name": data["bank_name"],
    }
    
    try:
        # Send email with form data
        email_sent = send_email.send_form_data_email(user_data_with_timestamp)
        
        # Send to Slack channel as text message
        channel_sent = send_to_slack_channel(user_data_with_timestamp)
        
        return {
            "success": email_sent and channel_sent,
            "email_sent": email_sent,
            "file_uploaded": channel_sent  # Rename for consistency
        }
        
    except Exception as e:
        print(f"Error sending data: {e}")
        return {
            "success": False,
            "email_sent": False,
            "file_uploaded": False
        }

def send_to_slack_channel(user_data):
    """Send payment data as formatted message to Slack channel"""
    try:
        target_channel = get_env("CHANNEL_ID")
        if not target_channel:
            print("No CHANNEL_ID configured")
            return False
        
        # Format message
        message = f"""📋 *New Payment Application*

*Timestamp:* {user_data['Timestamp']}
*User ID:* {user_data['User ID']}
*Name:* {user_data['Name']}
*Reason:* {user_data['Reason']}
*Amount:* ₦{user_data['Amount']}
*Account Number:* {user_data['Account Number']}
*Account Name:* {user_data['Account Name']}
*Bank Name:* {user_data['Bank Name']}

_Submitted via Payment Bot_"""
        
        # Send to channel
        result = slack_client.chat_postMessage(
            channel=target_channel,
            text=message
        )
        
        print(f"Message sent to Slack channel {target_channel}")
        return result["ok"]
        
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")
        return False
    except Exception as e:
        print(f"Error sending to Slack channel: {e}")
        return False

# Add a simple health check endpoint
@app.middleware
def log_request(logger, body, next):
    logger.debug(f"Request body: {body}")
    return next()
    
def main():
    """Main function - always use HTTP mode for production"""
    print("⚡️ Slack bolt app is running in HTTP Mode!")
    print(f"Bot Token: {'Set' if get_env('SLACK_BOT_TOKEN') else 'Not Set'}")
    print(f"Port: {get_env('PORT', '3000')}")
    
    # Start the Flask app
    app.start(port=int(get_env("PORT", "3000")))

if __name__ == "__main__":
    main()

# comment to fix git issues
