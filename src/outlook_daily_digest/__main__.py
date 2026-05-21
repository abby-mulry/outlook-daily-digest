from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .calendar_reader import CalendarReader
from .config import load_settings
from .graph_auth import GraphAuthenticator
from .graph_client import ReadOnlyGraphClient
from .inbox_reader import InboxReader
from .report_generator import generate_daily_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a read-only Outlook daily digest.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Report date, YYYY-MM-DD.")
    parser.add_argument("--messages", type=int, default=50, help="Inbox messages to inspect.")
    parser.add_argument("--output", type=Path, help="Optional markdown output path.")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date)
    settings = load_settings()
    authenticator = GraphAuthenticator(settings)
    graph_client = ReadOnlyGraphClient(authenticator, base_url=settings.graph_base_url)

    messages = InboxReader(graph_client).list_messages(top=args.messages)
    events = CalendarReader(graph_client, settings.outlook_timezone).list_events_for_day(
        report_date
    )
    report = generate_daily_report(messages, events, report_date=report_date)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
