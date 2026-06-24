"""
Gmail sending via SMTP.

GMAIL_APP_PASSWORD must be a Google App Password generated at
myaccount.google.com/apppasswords — not the account's regular password.
2FA must be enabled on the Google account before an App Password can be created.
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

_logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465


def send_email(to_address: str, subject: str, body: str) -> bool:
    sender = os.getenv("GMAIL_SENDER_ADDRESS", "")
    app_password = os.getenv("GMAIL_APP_PASSWORD", "")
    _logger.warning(
        "[DEBUG] gmail_service: GMAIL_SENDER_ADDRESS present=%r len=%d  GMAIL_APP_PASSWORD present=%r",
        bool(sender),
        len(sender),
        bool(app_password),
    )
    if not sender or not app_password:
        _logger.warning("[DEBUG] gmail_service: env vars missing — sender_present=%r password_present=%r — aborting", bool(sender), bool(app_password))
        return False

    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT, context=context) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        _logger.error("Gmail send failed to %s: %s", to_address, exc)
        return False
