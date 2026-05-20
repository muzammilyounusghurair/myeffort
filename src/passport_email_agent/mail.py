from __future__ import annotations

import imaplib
import smtplib
import time
from dataclasses import dataclass
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, make_msgid, parseaddr

from passport_email_agent.config import AgentConfig
from passport_email_agent.models import Attachment, InboundEmail


class EmailError(RuntimeError):
    """Raised when an email send or receive operation fails."""


@dataclass(frozen=True)
class SentEmail:
    message_id: str
    subject: str


class SmtpImapEmailClient:
    """SMTP sender and IMAP polling receiver used by the passport agent."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> SentEmail:
        message = EmailMessage()
        message["From"] = self._format_sender()
        message["To"] = to_address
        message["Subject"] = subject
        message_id = make_msgid()
        message["Message-ID"] = message_id
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to
        message.set_content(body)

        try:
            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port, timeout=30) as smtp:
                if self._config.smtp_starttls:
                    smtp.starttls()
                smtp.login(self._config.smtp_username, self._config.smtp_password)
                smtp.send_message(message)
        except OSError as exc:
            raise EmailError(f"Failed to send email to {to_address}: {exc}") from exc

        return SentEmail(message_id=message_id, subject=subject)

    def wait_for_reply(
        self,
        *,
        expected_sender: str,
        correlation_id: str,
        timeout_seconds: int,
        poll_interval_seconds: int,
    ) -> InboundEmail:
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            reply = self.find_reply(
                expected_sender=expected_sender,
                correlation_id=correlation_id,
            )
            if reply:
                return reply
            time.sleep(poll_interval_seconds)

        raise EmailError(
            f"No reply containing correlation id {correlation_id} arrived within "
            f"{timeout_seconds} seconds."
        )

    def find_reply(self, *, expected_sender: str, correlation_id: str) -> InboundEmail | None:
        try:
            with self._imap_connection() as imap:
                status, _ = imap.select(self._config.mailbox)
                if status != "OK":
                    raise EmailError(f"Could not select mailbox {self._config.mailbox}.")

                status, data = imap.search(None, "UNSEEN")
                if status != "OK":
                    raise EmailError("Could not search mailbox for unseen replies.")

                for message_id in reversed(data[0].split()):
                    status, message_data = imap.fetch(message_id, "(RFC822)")
                    if status != "OK" or not message_data:
                        continue
                    raw_message = next(
                        (part[1] for part in message_data if isinstance(part, tuple)),
                        None,
                    )
                    if not raw_message:
                        continue
                    inbound = self._parse_message(raw_message)
                    if self._is_matching_reply(inbound, expected_sender, correlation_id):
                        return inbound
        except OSError as exc:
            raise EmailError(f"Failed to read inbox replies: {exc}") from exc

        return None

    def _imap_connection(self) -> imaplib.IMAP4:
        if self._config.imap_ssl:
            imap: imaplib.IMAP4 = imaplib.IMAP4_SSL(
                self._config.imap_host,
                self._config.imap_port,
            )
        else:
            imap = imaplib.IMAP4(self._config.imap_host, self._config.imap_port)
        imap.login(self._config.imap_username, self._config.imap_password)
        return imap

    def _format_sender(self) -> str:
        display_name = "Passport Email Agent"
        local, _, domain = self._config.smtp_from.partition("@")
        if local and domain:
            return str(Address(display_name=display_name, username=local, domain=domain))
        return self._config.smtp_from

    def _parse_message(self, raw_message: bytes) -> InboundEmail:
        message = BytesParser(policy=policy.default).parsebytes(raw_message)
        body_parts: list[str] = []
        attachments: list[Attachment] = []

        for part in message.walk():
            if part.is_multipart():
                continue

            content_disposition = part.get_content_disposition()
            filename = part.get_filename()
            content_type = part.get_content_type()

            if content_disposition == "attachment" or filename:
                attachments.append(
                    Attachment(
                        filename=filename or "attachment",
                        content_type=content_type,
                        payload=part.get_payload(decode=True) or b"",
                    )
                )
                continue

            if content_type == "text/plain":
                content = part.get_content()
                if isinstance(content, str):
                    body_parts.append(content)

        sender = parseaddr(message.get("From", ""))[1]
        return InboundEmail(
            sender=sender,
            subject=message.get("Subject", ""),
            body="\n".join(body_parts),
            message_id=message.get("Message-ID"),
            attachments=tuple(attachments),
        )

    def _is_matching_reply(
        self,
        inbound: InboundEmail,
        expected_sender: str,
        correlation_id: str,
    ) -> bool:
        sender_matches = parseaddr(inbound.sender)[1].lower() == expected_sender.lower()
        if not sender_matches:
            all_addresses = [address.lower() for _, address in getaddresses([inbound.sender])]
            sender_matches = expected_sender.lower() in all_addresses

        haystack = f"{inbound.subject}\n{inbound.body}".lower()
        return sender_matches and correlation_id.lower() in haystack and bool(inbound.attachments)
