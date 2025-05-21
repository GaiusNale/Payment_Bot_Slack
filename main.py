from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from decouple import config
import re
import csv
import os
from datetime import datetime
import pandas as pd
import send_email
from slack_sdk import WebClient


# Initialize Slack app with bot token
app = App(token=config("SLACK_BOT_TOKEN"))
slack_client = WebClient(token=config("SLACK_BOT_TOKEN"))


# Define conversation states
STATES = {
    "IDLE": 0,
    "NAME": 1,
    "REASON": 3,
    "AMOUNT": 4,
    "ACCOUNT_NUM": 5,
    "ACCOUNT_NAME": 6,
    "BANK_NAME": 7,
    "CONFIRM": 8
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
    set_user_state(user_id, STATES["NAME"])
    say("Please enter your name:")

@app.command("/cancel")
def handle_cancel_command(ack, say, command):
    ack()
    user_id = command["user_id"]
    clear_user_data(user_id)
    say("Application canceled. Use `/form` to fill the form again.")

@app.message("")
def handle_dm(message, say):
    """Handle direct messages based on user state"""
    user_id = message["user"]
    text = message["text"]
    
    # Skip if message is from bot itself
    if message.get("bot_id"):
        return
    
    state = get_user_state(user_id)
    data = get_user_data(user_id)
    
    # Process based on current state
    if state == STATES["NAME"]:
        data["name"] = text
        set_user_state(user_id, STATES["REASON"])
        say("Please enter your reason for payment:")
        
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
            # Save to CSV and Excel
            save_result = save_user_data(data)
            
            if save_result["success"]:
                if save_result["email_sent"]:
                    say("Your application has been submitted successfully, and the accountant has been notified. ✅")
                else:
                    say("Your application was saved, but there was an error notifying the accountant. Please contact support.")
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

def csv_to_excel(csv_file, excel_file):
    """Convert CSV to Excel format"""
    try:
        df = pd.read_csv(csv_file)
        df.to_excel(excel_file, index=False)
        print(f"Converted {csv_file} to {excel_file}")
        return True
    except FileNotFoundError:
        print(f"Error: {csv_file} not found")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def save_user_data(data):
    """Save user data to CSV and Excel files"""
    csv_file_path = "payment_data.csv"
    excel_file_path = "payment_data.xlsx"
    target_channel = config("CHANNEL_ID", default=None)
    
    # Prepare the user data with timestamp
    user_data_with_timestamp = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Name": data["name"],
        "Reason": data["reason"],
        "Amount": data["amount"],
        "Account Number": data["accountnumber"],
        "Account Name": data["accountname"],
        "Bank Name": data["bank_name"],
    }
    
    try:
        file_exists = os.path.isfile(csv_file_path)
        
        # Write to CSV
        with open(csv_file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=user_data_with_timestamp.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(user_data_with_timestamp)
        
        # Convert to Excel
        excel_converted = csv_to_excel(csv_file_path, excel_file_path)

        # Send the file to a slack channel 

        file_uploaded = False
        if excel_converted:
            try:
                with open(excel_file_path, "rb") as file:
                    result = slack_client.files_upload_v2(
                        channels=target_channel,
                        file=file,
                        filename="Payment Data.xlsx",
                        title=f"Payment Data - {user_data_with_timestamp['Timestamp']}",
                    )
                    file_uploaded = result["ok"]
                    print("File uploaded to Slack")
            except Exception as e:
                print(f"Error uploading file to Slack: {e}")

        # Send email if Excel conversion succeeded
        email_sent = False
        if excel_converted:
            email_sent = send_email.send_email_via_gmail(excel_file_path)
        
        return {
            "success": True,
            "excel_converted": excel_converted,
            "email_sent": email_sent,
            "file_uploaded": file_uploaded
        }
        
    except Exception as e:
        print(f"Error saving data: {e}")
        return {
            "success": False,
            "excel_converted": False,
            "email_sent": False,
            "file_uploaded": False
        }

def main():
    # For development: Use Socket Mode
    # For production: Use HTTP endpoints
    if config("SLACK_APP_TOKEN", default=None):
        # Socket Mode (recommended for development)
        handler = SocketModeHandler(app, config("SLACK_APP_TOKEN"))
        print("⚡️ Slack bolt app is running in Socket Mode!")
        handler.start()
    else:
        # HTTP Mode (for production)
        print("⚡️ Slack bolt app is running in HTTP Mode!")
        app.start(port=int(config("PORT", default=3000)))

if __name__ == "__main__":
    main()