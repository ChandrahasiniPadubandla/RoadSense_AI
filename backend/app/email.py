"""SMTP helpers for transactional email."""

import os
import smtplib
from email.message import EmailMessage


class EmailDeliveryError(Exception):
    """Raised when the application cannot deliver an email."""


def send_password_reset_otp(recipient: str, otp: str) -> None:
    """Send a short-lived password-reset code to ``recipient``."""
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM_EMAIL")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    if not host or not sender:
        raise EmailDeliveryError("SMTP_HOST and SMTP_FROM_EMAIL must be configured")
    if bool(username) != bool(password):
        raise EmailDeliveryError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")

    message = EmailMessage()
    message["Subject"] = "Your RoadSense AI password reset code"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Your RoadSense AI password reset code is: {otp}\n\n"
        "It expires in 15 minutes. Do not share this code with anyone."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    timeout = int(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}

    try:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Unable to send OTP email") from exc
