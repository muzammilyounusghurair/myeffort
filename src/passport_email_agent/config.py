from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_RECIPIENT = "muzammil.younus@al-ghurair.com"


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class AgentConfig:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_starttls: bool
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    imap_ssl: bool
    mailbox: str
    poll_interval_seconds: int
    reply_timeout_seconds: int
    default_recipient: str = DEFAULT_RECIPIENT

    @classmethod
    def from_env(cls) -> "AgentConfig":
        smtp_username = os.environ["SMTP_USERNAME"]
        imap_username = os.getenv("IMAP_USERNAME", smtp_username)
        return cls(
            smtp_host=os.environ["SMTP_HOST"],
            smtp_port=_get_int("SMTP_PORT", 587),
            smtp_username=smtp_username,
            smtp_password=os.environ["SMTP_PASSWORD"],
            smtp_from=os.getenv("SMTP_FROM", smtp_username),
            smtp_starttls=_get_bool("SMTP_STARTTLS", True),
            imap_host=os.environ["IMAP_HOST"],
            imap_port=_get_int("IMAP_PORT", 993),
            imap_username=imap_username,
            imap_password=os.getenv("IMAP_PASSWORD", os.environ["SMTP_PASSWORD"]),
            imap_ssl=_get_bool("IMAP_SSL", True),
            mailbox=os.getenv("IMAP_MAILBOX", "INBOX"),
            poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 30),
            reply_timeout_seconds=_get_int("REPLY_TIMEOUT_SECONDS", 1800),
            default_recipient=os.getenv("PASSPORT_AGENT_RECIPIENT", DEFAULT_RECIPIENT),
        )
