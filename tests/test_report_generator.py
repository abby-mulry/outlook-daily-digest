from __future__ import annotations

from datetime import date
import unittest

from outlook_daily_digest.calendar_reader import OutlookEvent
from outlook_daily_digest.inbox_reader import OutlookMessage
from outlook_daily_digest.report_generator import generate_daily_report


class ReportGeneratorTests(unittest.TestCase):
    def test_generate_daily_report_groups_and_flags_work(self) -> None:
        messages = [
            OutlookMessage(
                id="1",
                subject="Please review proposal",
                sender_name="Casey Customer",
                sender_email="casey@example.com",
                received_at="2026-05-21T09:00:00",
                preview="Can you approve the latest version before the meeting?",
                web_link="https://outlook.office.com/mail/1",
                is_read=False,
                conversation_id="thread-1",
                importance="normal",
                categories=(),
            ),
            OutlookMessage(
                id="2",
                subject="Blocked on data export",
                sender_name="Dev Partner",
                sender_email="dev@partner.test",
                received_at="2026-05-21T10:00:00",
                preview="We are waiting on access to finish the export.",
                web_link="",
                is_read=True,
                conversation_id="thread-2",
                importance="high",
                categories=(),
            ),
        ]
        events = [
            OutlookEvent(
                id="event-1",
                subject="Proposal review",
                organizer_name="Casey Customer",
                organizer_email="casey@example.com",
                start="2026-05-21T13:00:00",
                end="2026-05-21T13:30:00",
                location="Teams",
                attendees=("Casey Customer",),
                web_link="",
                is_cancelled=False,
            )
        ]

        report = generate_daily_report(messages, events, report_date=date(2026, 5, 21))

        self.assertIn("# Outlook Daily Digest - 2026-05-21", report)
        self.assertIn("### example.com", report)
        self.assertIn("Please review proposal", report)
        self.assertIn("Blocked on data export", report)
        self.assertIn("### Proposal review", report)


if __name__ == "__main__":
    unittest.main()
