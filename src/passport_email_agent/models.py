from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Attachment:
    """Email attachment payload supplied to the passport extractor."""

    filename: str
    content_type: str
    payload: bytes


@dataclass(frozen=True)
class InboundEmail:
    """Inbound email reply that may contain one or more passport files."""

    sender: str
    subject: str
    body: str
    message_id: str | None
    attachments: tuple[Attachment, ...]


@dataclass(frozen=True)
class PassportData:
    """Structured passport fields extracted from a supplied document."""

    full_name: str
    passport_number: str
    expiry_date: date
    source_file: str
    confidence: float | None = None

    def as_email_body(self) -> str:
        confidence_line = (
            f"\nConfidence: {self.confidence:.0%}" if self.confidence is not None else ""
        )
        return (
            "Passport details extracted from your file:\n\n"
            f"Name: {self.full_name}\n"
            f"Passport Number: {self.passport_number}\n"
            f"Expiry Date: {self.expiry_date.isoformat()}\n"
            f"Source File: {self.source_file}"
            f"{confidence_line}\n\n"
            "Please verify these details before using them."
        )
