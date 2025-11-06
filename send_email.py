import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime

def send_form_data_email(user_data):
    """Send plain-text form data via email (no attachment). Sends to second recipient if amount > ₦30,000."""
    try:
        # Email configuration from environment variables
        sender_email = os.environ.get("EMAIL_SENDER")
        sender_password = os.environ.get("EMAIL_PASSWORD")
        receiver_email = os.environ.get("EMAIL_RECEIVER")
        receiver_email2 = os.environ.get("EMAIL_RECEIVER2")

        if not all([sender_email, sender_password, receiver_email]):
            print("Missing email configuration in environment variables")
            return False

        # Check amount threshold (30,000 naira)
        try:
            amount_str = str(user_data.get('Amount', '0')).replace(',', '').replace('₦', '')
            amount_value = float(amount_str)
            send_to_second_recipient = amount_value > 30000
        except (ValueError, TypeError):
            amount_value = 0
            send_to_second_recipient = False

        # Determine recipients
        recipients = [receiver_email]
        if send_to_second_recipient and receiver_email2:
            recipients.append(receiver_email2)
            print(f"Amount ₦{amount_value:,.2f} exceeds threshold - sending to both recipients")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        subject_prefix = "[HIGH AMOUNT] " if send_to_second_recipient else ""
        msg['Subject'] = f"{subject_prefix}Payment Application - {user_data.get('Name', 'Unknown')}"

        # Add body to email with all form data (plain text)
        body = f"""
New Payment Application Submitted
{'⚠️ HIGH AMOUNT ALERT ⚠️' if send_to_second_recipient else ''}

Application Details:
==================
Timestamp: {user_data.get('Timestamp', 'N/A')}
User ID: {user_data.get('User ID', 'N/A')}
Name: {user_data.get('Name', 'N/A')}
Reason: {user_data.get('Reason', 'N/A')}
Amount: ₦{user_data.get('Amount', 'N/A')}
Account Number: {user_data.get('Account Number', 'N/A')}
Account Name: {user_data.get('Account Name', 'N/A')}
Bank Name: {user_data.get('Bank Name', 'N/A')}

Submitted via: Slack Payment Bot

Please process this payment request accordingly.

Best regards,
Payment Bot System
        """
        msg.attach(MIMEText(body, 'plain'))

        # Use Zoho SMTP SSL connection
        with smtplib.SMTP_SSL('smtppro.zoho.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())

        print(f"Form data email sent successfully to {len(recipients)} recipient(s)!")
        return True
    except Exception as e:
        print(f"Error sending form data email: {e}")
        return False


def test_email_config():
    """Test if email configuration is working"""
    sender_email = os.environ.get("EMAIL_SENDER", default=None)
    sender_password = os.environ.get("EMAIL_PASSWORD", default=None)
    receiver_email = os.environ.get("EMAIL_RECEIVER", default=None)
    receiver_email2 = os.environ.get("EMAIL_RECEIVER2", default=None)

    print("Testing email configuration...")
    print(f"Sender: {sender_email}")
    print(f"Receiver 1: {receiver_email}")
    print(f"Receiver 2: {receiver_email2 if receiver_email2 else 'Not configured'}")
    print(f"Password: {'*' * len(sender_password) if sender_password else 'Not set'}")

    if not all([sender_email, sender_password, receiver_email]):
        print("Error: Missing email configuration")
        return False

    try:
        # ✅ Test Zoho SMTP SSL connection
        with smtplib.SMTP_SSL("smtppro.zoho.com", 465) as server:
            server.login(sender_email, sender_password)
        print("✅ Email configuration is working (SSL 465)!")
        return True
    except Exception as e:
        print(f"Email configuration error: {e}")
        return False


if __name__ == "__main__":
    test_email_config()
