import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import get_config


def send_email(to_email: str, subject: str, message_body: str) -> bool:
    """
    Sends an email using the Gmail SMTP server based on environment variables.
    Returns False if email credentials are not configured.
    """
    config = get_config()
    
    sender_email = config.email.smtp_username
    sender_password = config.email.smtp_password

    if not sender_email or not sender_password:
        print("Error: SMTP_USERNAME or SMTP_PASSWORD not configured. Email not sent.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = config.email.smtp_from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))

        # Connect to SMTP server
        with smtplib.SMTP(config.email.smtp_server, config.email.smtp_port) as server:
            if config.email.smtp_use_tls:
                server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(config.email.smtp_from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
