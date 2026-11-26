"""Transactional email behind an interface. 'outbox' keeps messages in memory for development and tests."""

import smtplib
import ssl
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    kind: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EmailSender(Protocol):
    def send(self, message: OutgoingEmail) -> None: ...


class OutboxEmailSender:
    def __init__(self, limit: int = 200) -> None:
        self._messages: list[OutgoingEmail] = []
        self._lock = threading.Lock()
        self._limit = limit

    def send(self, message: OutgoingEmail) -> None:
        with self._lock:
            self._messages.append(message)
            del self._messages[: -self._limit]

    def messages(self, to: str | None = None) -> list[OutgoingEmail]:
        with self._lock:
            return [m for m in self._messages if to is None or m.to == to.lower()]


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        if not settings.smtp_host:
            raise ValueError("PDNA_SMTP_HOST is required when PDNA_EMAIL_PROVIDER=smtp")
        self._s = settings

    def send(self, message: OutgoingEmail) -> None:
        msg = EmailMessage()
        msg["From"] = self._s.email_from
        msg["To"] = message.to
        msg["Subject"] = message.subject
        msg.set_content(message.text)
        with smtplib.SMTP(self._s.smtp_host or "", self._s.smtp_port, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if self._s.smtp_username and self._s.smtp_password:
                smtp.login(self._s.smtp_username, self._s.smtp_password.get_secret_value())
            smtp.send_message(msg)


def make_email_sender(settings: Settings) -> EmailSender:
    if settings.email_provider == "smtp":
        return SmtpEmailSender(settings)
    return OutboxEmailSender()
