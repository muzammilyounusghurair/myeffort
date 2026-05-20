from __future__ import annotations

from datetime import date

from passport_email_agent.agent import PassportEmailAgent
from passport_email_agent.mail import SentEmail
from passport_email_agent.models import Attachment, InboundEmail


class FakeEmailClient:
    def __init__(self) -> None:
        self.sent: list[dict[str, str | None]] = []
        self.correlation_id: str | None = None

    def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> SentEmail:
        self.sent.append(
            {
                "to_address": to_address,
                "subject": subject,
                "body": body,
                "in_reply_to": in_reply_to,
            }
        )
        if subject.startswith("Passport file request"):
            self.correlation_id = subject.split("[", maxsplit=1)[1].rstrip("]")
        return SentEmail(message_id=f"<sent-{len(self.sent)}@example.com>", subject=subject)

    def wait_for_reply(
        self,
        *,
        expected_sender: str,
        correlation_id: str,
        timeout_seconds: int,
        poll_interval_seconds: int,
    ) -> InboundEmail:
        assert expected_sender == "muzammil.younus@al-ghurair.com"
        assert correlation_id == self.correlation_id
        return InboundEmail(
            sender=expected_sender,
            subject=f"Re: Passport file request [{correlation_id}]",
            body=f"Reference: {correlation_id}",
            message_id="<reply@example.com>",
            attachments=(
                Attachment(
                    filename="passport.txt",
                    content_type="text/plain",
                    payload=(
                        b"Name: Muzammil Younus\n"
                        b"Passport Number: A1234567\n"
                        b"Date of Expiry: 20 May 2031\n"
                    ),
                ),
            ),
        )


def test_agent_requests_passport_extracts_attachment_and_sends_result() -> None:
    client = FakeEmailClient()
    agent = PassportEmailAgent(
        email_client=client,
        timeout_seconds=1,
        poll_interval_seconds=1,
    )

    result = agent.request_passport_and_reply("muzammil.younus@al-ghurair.com")

    assert len(client.sent) == 2
    assert client.sent[0]["subject"].startswith("Passport file request [passport-")
    assert client.sent[1]["subject"].startswith("Extracted passport details [passport-")
    assert client.sent[1]["in_reply_to"] == "<reply@example.com>"
    assert "Name: MUZAMMIL YOUNUS" in str(client.sent[1]["body"])
    assert "Passport Number: A1234567" in str(client.sent[1]["body"])
    assert result.passport_data.expiry_date == date(2031, 5, 20)
