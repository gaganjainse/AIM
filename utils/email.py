from __future__ import annotations

import logging
from typing import Optional

from flask import current_app
from flask_mail import Mail, Message

mail = Mail()
logger = logging.getLogger(__name__)


def email_enabled() -> bool:
    return bool(current_app.config.get("MAIL_USERNAME") and current_app.config.get("MAIL_PASSWORD"))


def send_email(to: str, subject: str, body: str) -> bool:
    """Best-effort email sender. Email is optional; missing config never breaks the app."""
    if not to or not email_enabled():
        return False
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        )
        mail.send(msg)
        return True
    except Exception as exc:
        logger.error("Email send failed: %s", exc, exc_info=True)
        return False
