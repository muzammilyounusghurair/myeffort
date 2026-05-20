from __future__ import annotations

import argparse
import sys
from pathlib import Path

from passport_email_agent.agent import PassportEmailAgent
from passport_email_agent.config import AgentConfig, DEFAULT_RECIPIENT
from passport_email_agent.extractor import PassportExtractor
from passport_email_agent.mail import EmailError, SmtpImapEmailClient
from passport_email_agent.web import run_upload_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="passport-email-agent",
        description=(
            "Accept a passport file through a simple upload UI, then extract "
            "the passport holder name, passport number, and expiry date."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the passport upload web UI.")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)

    email_parser = subparsers.add_parser("email", help="Run the email request workflow.")
    email_parser.add_argument(
        "--recipient",
        default=None,
        help=f"Recipient email address. Defaults to env or {DEFAULT_RECIPIENT}.",
    )
    email_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=None,
        help="How long to wait for a reply before failing.",
    )
    email_parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=None,
        help="How often to poll the inbox for a matching reply.",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract passport details from a local file without sending email.",
    )
    extract_parser.add_argument("file", type=Path)
    extract_parser.add_argument("--content-type", default="")

    parser.set_defaults(command="run")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        return _run_extract(args)
    if args.command == "email":
        return _run_email_agent(args)
    return _run_upload_ui(args)


def _run_upload_ui(args: argparse.Namespace) -> int:
    run_upload_server(host=args.host, port=args.port)
    return 0


def _run_email_agent(args: argparse.Namespace) -> int:
    try:
        config = AgentConfig.from_env()
        recipient = args.recipient or config.default_recipient
        email_client = SmtpImapEmailClient(config)
        agent = PassportEmailAgent(
            email_client=email_client,
            timeout_seconds=args.timeout_seconds or config.reply_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds or config.poll_interval_seconds,
        )
        result = agent.request_passport_and_reply(recipient)
    except (EmailError, KeyError, ValueError) as exc:
        print(f"Agent failed: {exc}", file=sys.stderr)
        return 1

    print("Passport details extracted and emailed successfully.")
    print(f"Name: {result.passport_data.full_name}")
    print(f"Passport Number: {result.passport_data.passport_number}")
    print(f"Expiry Date: {result.passport_data.expiry_date.isoformat()}")
    return 0


def _run_extract(args: argparse.Namespace) -> int:
    extractor = PassportExtractor()
    try:
        payload = args.file.read_bytes()
        data = extractor.extract(
            payload=payload,
            filename=args.file.name,
            content_type=args.content_type,
        )
    except OSError as exc:
        print(f"Could not read file: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1

    print(data.as_email_body())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
