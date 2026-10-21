"""SMTP helpers for transactional email."""

import os
import smtplib
from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class EmailDeliveryError(Exception):
    """Raised when the application cannot deliver an email."""


def _get_smtp_settings() -> tuple[str, str, str | None, str | None]:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM_EMAIL")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    if not host or not sender:
        raise EmailDeliveryError("SMTP_HOST and SMTP_FROM_EMAIL must be configured")
    if bool(username) != bool(password):
        raise EmailDeliveryError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")

    return host, sender, username, password


def _smtp_error_message(exc: Exception, email_kind: str) -> str:
    details = str(exc).strip() or exc.__class__.__name__

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        username = os.getenv("SMTP_USERNAME", "")
        if username.lower().endswith("@gmail.com"):
            return (
                f"Unable to send {email_kind} email: SMTP authentication failed. "
                "For Gmail, SMTP_PASSWORD must be a Google App Password, not your regular Gmail password."
            )
        return f"Unable to send {email_kind} email: SMTP authentication failed: {details}"

    return f"Unable to send {email_kind} email: {details}"


def _send_smtp_message(message: EmailMessage, email_kind: str) -> None:
    host, _, username, password = _get_smtp_settings()
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
        raise EmailDeliveryError(_smtp_error_message(exc, email_kind)) from exc


def send_password_reset_otp(recipient: str, otp: str) -> None:
    """Send a short-lived password-reset code to ``recipient``."""
    _, sender, _, _ = _get_smtp_settings()

    message = EmailMessage()
    message["Subject"] = "Your Metrivon AI password reset code"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Your Metrivon AI password reset code is: {otp}\n\n"
        "It expires in 15 minutes. Do not share this code with anyone."
    )

    _send_smtp_message(message, "password reset")


def send_email_verification_otp(recipient: str, otp: str) -> None:
    """Send a short-lived email-verification code to ``recipient``."""
    _, sender, _, _ = _get_smtp_settings()

    message = EmailMessage()
    message["Subject"] = "Verify your Metrivon AI email"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Your Metrivon AI email verification code is: {otp}\n\n"
        "It expires in 15 minutes. Do not share this code with anyone."
    )

    _send_smtp_message(message, "verification")
