from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from passport_email_agent.extractor import PassportExtractionError, PassportExtractor
from passport_email_agent.mail import SentEmail
from passport_email_agent.models import Attachment, InboundEmail, PassportData


class EmailClient(Protocol):
    def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> SentEmail:
        ...

    def wait_for_reply(
        self,
        *,
        expected_sender: str,
        correlation_id: str,
        timeout_seconds: int,
        poll_interval_seconds: int,
    ) -> InboundEmail:
        ...


@dataclass(frozen=True)
class AgentResult:
    request_message_id: str
    reply_message_id: str | None
    result_message_id: str
    passport_data: PassportData


class PassportEmailAgent:
    """Coordinates the passport email request, reply polling, extraction, and response."""

    def __init__(
        self,
        *,
        email_client: EmailClient,
        extractor: PassportExtractor | None = None,
        timeout_seconds: int = 1800,
        poll_interval_seconds: int = 30,
    ) -> None:
        self._email_client = email_client
        self._extractor = extractor or PassportExtractor()
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    def request_passport_and_reply(self, recipient: str) -> AgentResult:
        correlation_id = self._new_correlation_id()
        request = self._send_passport_request(recipient, correlation_id)
        reply = self._email_client.wait_for_reply(
            expected_sender=recipient,
            correlation_id=correlation_id,
            timeout_seconds=self._timeout_seconds,
            poll_interval_seconds=self._poll_interval_seconds,
        )
        passport_data = self._extract_first_valid_passport(reply.attachments)
        result = self._send_extracted_details(
            recipient=recipient,
            passport_data=passport_data,
            correlation_id=correlation_id,
            in_reply_to=reply.message_id,
        )

        return AgentResult(
            request_message_id=request.message_id,
            reply_message_id=reply.message_id,
            result_message_id=result.message_id,
            passport_data=passport_data,
        )

    def _send_passport_request(self, recipient: str, correlation_id: str) -> SentEmail:
        subject = f"Passport file request [{correlation_id}]"
        body = (
            "Hello,\n\n"
            "Please reply to this email with your passport file attached. "
            "The agent will extract the passport holder name, passport number, "
            "and expiry date from the file.\n\n"
            f"Reference: {correlation_id}\n\n"
            "Thank you."
        )
        return self._email_client.send_email(
            to_address=recipient,
            subject=subject,
            body=body,
        )

    def _send_extracted_details(
        self,
        *,
        recipient: str,
        passport_data: PassportData,
        correlation_id: str,
        in_reply_to: str | None,
    ) -> SentEmail:
        subject = f"Extracted passport details [{correlation_id}]"
        return self._email_client.send_email(
            to_address=recipient,
            subject=subject,
            body=passport_data.as_email_body(),
            in_reply_to=in_reply_to,
        )

    def _extract_first_valid_passport(self, attachments: tuple[Attachment, ...]) -> PassportData:
        if not attachments:
            raise PassportExtractionError("The reply did not include any attachments.")

        errors: list[str] = []
        for attachment in attachments:
            try:
                return self._extractor.extract_attachment(attachment)
            except PassportExtractionError as exc:
                errors.append(f"{attachment.filename}: {exc}")

        raise PassportExtractionError(
            "No attachment contained extractable passport details. "
            + " | ".join(errors)
        )

    def _new_correlation_id(self) -> str:
        return f"passport-{uuid4().hex[:12]}"
