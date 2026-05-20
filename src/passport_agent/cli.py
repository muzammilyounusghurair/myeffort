from __future__ import annotations

import argparse
import sys
from pathlib import Path

from passport_agent.extractor import PassportExtractor
from passport_agent.web import run_upload_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="passport-agent",
        description=(
            "Accept a passport file through a simple upload UI, then extract "
            "the passport holder name, passport number, and expiry date."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the passport upload web UI.")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract passport details from a local file.",
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
    return _run_upload_ui(args)


def _run_upload_ui(args: argparse.Namespace) -> int:
    run_upload_server(host=args.host, port=args.port)
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

    print(data.as_display_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
