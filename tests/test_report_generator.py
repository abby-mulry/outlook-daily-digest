from __future__ import annotations

from datetime import date
import unittest

from gmail_subscription_cleanup.inbox_reader import GmailMessage
from gmail_subscription_cleanup.report_generator import generate_cleanup_report


class ReportGeneratorTests(unittest.TestCase):
    def test_generate_cleanup_report_groups_subscription_candidates(self) -> None:
        messages = [
            GmailMessage(
                id="1",
                thread_id="thread-1",
                subject="Weekly product newsletter",
                sender_name="Product Updates",
                sender_email="news@example.com",
                received_at="2026-05-21T09:00:00",
                snippet="This week in product news, events, and offers.",
                label_ids=("INBOX",),
                headers={
                    "list-unsubscribe": "<mailto:unsubscribe@example.com>",
                    "list-id": "product.example.com",
                },
            ),
            GmailMessage(
                id="2",
                thread_id="thread-2",
                subject="Monthly product newsletter",
                sender_name="Product Updates",
                sender_email="news@example.com",
                received_at="2026-05-21T10:00:00",
                snippet="Recommended webinars and product insights.",
                label_ids=("INBOX",),
                headers={"list-unsubscribe": "<mailto:unsubscribe@example.com>"},
            ),
        ]

        report = generate_cleanup_report(messages, report_date=date(2026, 5, 21))

        self.assertIn("# Gmail Subscription Cleanup Report - 2026-05-21", report)
        self.assertIn("## Unsubscribe", report)
        self.assertIn("Product Updates <news@example.com>", report)
        self.assertIn("Unsubscribe metadata: 1 mailto target(s)", report)


if __name__ == "__main__":
    unittest.main()
