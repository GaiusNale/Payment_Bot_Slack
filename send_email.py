import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import datetime
import io

def send_form_data_email(user_data):
    """Send form data directly via email (no attachment)"""
    try:
        # Email configuration from environment variables
        sender_email = os.environ.get("EMAIL_SENDER")
        sender_password = os.environ.get("EMAIL_PASSWORD") 
        receiver_email = os.environ.get("EMAIL_RECEIVER")
        
        if not all([sender_email, sender_password, receiver_email]):
            print("Missing email configuration in environment variables")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"Payment Application - {user_data.get('Name', 'Unknown')}"
        
        # Add body to email with all form data
        body = f"""
        New Payment Application Submitted
        
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
        
        # Gmail SMTP configuration
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enable security
        server.login(sender_email, sender_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        
        print("Form data email sent successfully!")
        return True
        
    except Exception as e:
        print(f"Error sending form data email: {e}")
        return False

def send_form_data_with_excel(user_data, excel_file):
    """Send form data via email with Excel attachment"""
    try:
        # Email configuration from environment variables
        sender_email = os.environ.get("EMAIL_SENDER")
        sender_password = os.environ.get("EMAIL_PASSWORD") 
        receiver_email = os.environ.get("EMAIL_RECEIVER")
        
        if not all([sender_email, sender_password, receiver_email]):
            print("Missing email configuration in environment variables")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"Payment Application - {user_data.get('Name', 'Unknown')} (with Excel)"
        
        # Add body with form data
        body = f"""
        New Payment Application Submitted
        
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
        
        Please find the Excel file attached with the payment application details.
        
        Best regards,
        Payment Bot System
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach Excel file if provided
        if excel_file:
            try:
                excel_file.seek(0)  # Reset file pointer
                
                # Create attachment
                part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                part.set_payload(excel_file.getvalue())
                encoders.encode_base64(part)
                
                # Generate filename with timestamp
                filename = f"payment_application_{user_data.get('User ID', 'unknown')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                msg.attach(part)
                print(f"Excel file attached: {filename}")
                
            except Exception as e:
                print(f"Error attaching Excel file: {e}")
                # Continue without attachment
        
        # Gmail SMTP configuration
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enable security
        server.login(sender_email, sender_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        
        print("Email with Excel attachment sent successfully!")
        return True
        
    except Exception as e:
        print(f"Error sending email with Excel: {e}")
        return False

def send_notification_email(user_data):
    """Send a notification email without attachment for quick alerts"""
    # Load environment variables
    sender_email = os.environ.get("EMAIL_SENDER", default=None)
    sender_password = os.environ.get("EMAIL_PASSWORD", default=None)
    receiver_email = os.environ.get("EMAIL_RECEIVER", default=None)

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
Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
    sender_email = os.environ.get("EMAIL_SENDER", default=None)
    sender_password = os.environ.get("EMAIL_PASSWORD", default=None)
    receiver_email = os.environ.get("EMAIL_RECEIVER", default=None)

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