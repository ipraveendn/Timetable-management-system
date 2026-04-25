"""
VYUHA Email Tool
SMTP-based email sending utility for transactional emails
"""

import smtplib
from email.message import EmailMessage
import os
from typing import Optional

def create_email_message(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> EmailMessage:
    """
    Create a properly formatted email message.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Plain text body
        html_body: Optional HTML-formatted body

    Returns:
        EmailMessage object ready for sending
    """
    msg = EmailMessage()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_FROM_EMAIL", "noreply@institution.edu")

    if html_body:
        msg.set_content(body)
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(body)

    return msg

def send_email(
    smtp_user: str,
    smtp_pass: str,
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """
    Send an email via SMTP server with proper error handling.

    Returns:
        True if sent successfully, False otherwise
    """
    msg = create_email_message(to_email, subject, body, html_body)

    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        # Connect and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        # In production, this would log to monitoring system
        print(f"❌ Email send failed: {str(e)}")
        return False

def generate_verification_email(to_email: str, verification_url: str) -> tuple:
    """
    Generate email content for user verification.

    Args:
        to_email: Recipient email
        verification_url: URL for email verification link

    Returns:
        (subject, body) tuple for email sending
    """
    verification_link = f"{verification_url}?token=verify_email"
    subject = "Email Verification Required"
    body = f"""
    Dear User,

    Please verify your email address by clicking the link below:
    {verification_link}

    If you did not request this, please ignore this email.

    Best regards,
    VYUHA Team
    """
    return subject, body

def generate_welcome_email(to_email: str, user_name: str) -> tuple:
    """
    Generate welcome email content for new users.

    Args:
        to_email: Recipient email
        user_name: Recipient's name

    Returns:
        (subject, body) tuple for email sending
    """
    subject = "Welcome to VYUHA Academy!"
    body = f"""
    Hello {user_name},

    Welcome to VYUHA Academy! We're excited to have you join our community of learners.

    Here's what you need to know:
    • Access your student dashboard at: {os.getenv('APP_URL', 'https://vyuha.edu')}/dashboard
    • Check your upcoming classes and schedules
    • Receive announcements and important updates

    If you have any questions, reply to this email or contact support.

    Best regards,
    VYUHA Team
    """
    return subject, body