from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Attachment:
    """Uploaded file payload supplied to the passport extractor."""

    filename: str
    content_type: str
    payload: bytes


@dataclass(frozen=True)
class PassportData:
    """Structured passport fields extracted from a supplied document."""

    full_name: str
    passport_number: str
    expiry_date: date
    source_file: str
    confidence: float | None = None

    def as_display_text(self) -> str:
        confidence_line = (
            f"\nConfidence: {self.confidence:.0%}" if self.confidence is not None else ""
        )
        return (
            "Passport details extracted from the uploaded file:\n\n"
            f"Name: {self.full_name}\n"
            f"Passport Number: {self.passport_number}\n"
            f"Expiry Date: {self.expiry_date.isoformat()}\n"
            f"Source File: {self.source_file}"
            f"{confidence_line}\n\n"
            "Please verify these details before using them."
        )
