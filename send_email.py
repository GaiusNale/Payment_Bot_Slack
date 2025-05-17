from decouple import config
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime


def send_email_via_gmail(file_path):
    """Send email with attachment via Gmail SMTP"""
    # Load environment variables
    sender_email = config("EMAIL_SENDER", default=None)
    sender_password = config("EMAIL_PASSWORD", default=None)
    receiver_email = config("EMAIL_RECEIVER", default=None)

    if not sender_email or not sender_password or not receiver_email:
        print("Error: Missing email environment variables. Check your .env file.")
        return False

    # Email content
    subject = f"New Payment Application - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    body = """A new payment application has been received via Slack bot.

Please find the attached Excel file for complete details.

This is an automated message from the Payment Bot.
"""

    # Create the email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Attach the file
    try:
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(file_path)}",
            )
            msg.attach(part)
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        return False
    except Exception as e:
        print(f"Error attaching file: {e}")
        return False

    # Send the email using Gmail SMTP
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:  # Use SMTP_SSL for port 465
            server.login(sender_email, sender_password)  # Log in using App Password
            server.send_message(msg)  # Send the email
            print(f"Email sent successfully to {receiver_email}!")
            return True
    except smtplib.SMTPAuthenticationError:
        print("Error: Authentication failed. Check your email and app password.")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_notification_email(user_data):
    """Send a notification email without attachment for quick alerts"""
    # Load environment variables
    sender_email = config("EMAIL_SENDER", default=None)
    sender_password = config("EMAIL_PASSWORD", default=None)
    receiver_email = config("EMAIL_RECEIVER", default=None)

    if not sender_email or not sender_password or not receiver_email:
        print("Error: Missing email environment variables.")
        return False

    # Email content with user details
    subject = f"New Payment Request - {user_data.get('name', 'Unknown')}"
    body = f"""New payment application received:

Name: {user_data.get('name', 'N/A')}
Email: {user_data.get('email', 'N/A')}
Reason: {user_data.get('reason', 'N/A')}
Amount: ₦{user_data.get('amount', 'N/A')}
Account Number: {user_data.get('accountnumber', 'N/A')}
Account Name: {user_data.get('accountname', 'N/A')}
Bank Name: {user_data.get('bank_name', 'N/A')}

Submitted via: Slack Bot
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the attached Excel file for complete records.
"""

    # Create the email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("Notification email sent successfully!")
            return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


# Test function for email configuration
def test_email_config():
    """Test if email configuration is working"""
    sender_email = config("EMAIL_SENDER", default=None)
    sender_password = config("EMAIL_PASSWORD", default=None)
    receiver_email = config("EMAIL_RECEIVER", default=None)

    print("Testing email configuration...")
    print(f"Sender: {sender_email}")
    print(f"Receiver: {receiver_email}")
    print(f"Password: {'*' * len(sender_password) if sender_password else 'Not set'}")

    if not all([sender_email, sender_password, receiver_email]):
        print("Error: Missing email configuration")
        return False

    try:
        # Test SMTP connection
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            print("Email configuration is working!")
            return True
    except Exception as e:
        print(f"Email configuration error: {e}")
        return False


if __name__ == "__main__":
    # Test the email configuration when running directly
    test_email_config()