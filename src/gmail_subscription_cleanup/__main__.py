from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_settings
from .gmail_auth import GmailAuthenticator
from .inbox_reader import GmailInboxReader
from .report_generator import generate_cleanup_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a read-only Gmail subscription cleanup report."
    )
    parser.add_argument("--messages", type=int, default=250, help="Inbox messages to inspect.")
    parser.add_argument(
        "--query",
        help="Optional Gmail search query for the inbox scan. Defaults to GMAIL_QUERY.",
    )
    parser.add_argument(
        "--min-recurring-count",
        type=int,
        default=2,
        help="Messages from the same sender needed to count as recurring.",
    )
    parser.add_argument("--output", type=Path, help="Optional markdown output path.")
    args = parser.parse_args()

    settings = load_settings()
    service = GmailAuthenticator(settings).build_service()
    messages = GmailInboxReader(service, settings.user_id).list_messages(
        max_results=args.messages,
        query=args.query if args.query is not None else settings.default_query,
    )
    report = generate_cleanup_report(
        messages,
        min_recurring_count=args.min_recurring_count,
    )

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
