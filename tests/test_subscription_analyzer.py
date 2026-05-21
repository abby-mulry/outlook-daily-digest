from __future__ import annotations

import unittest

from gmail_subscription_cleanup.inbox_reader import GmailMessage
from gmail_subscription_cleanup.subscription_analyzer import (
    HUMAN_REVIEW,
    KEEP_ORGANIZE,
    UNSUBSCRIBE,
    analyze_subscription_candidates,
    parse_unsubscribe_metadata,
)


def message(
    sender: str,
    subject: str,
    preview: str,
    headers: dict[str, str] | None = None,
) -> GmailMessage:
    return GmailMessage(
        id=subject,
        thread_id=subject,
        subject=subject,
        sender_name=sender.split("@", 1)[0],
        sender_email=sender,
        received_at="2026-05-21T09:00:00",
        snippet=preview,
        label_ids=("INBOX",),
        headers=headers or {},
    )


class SubscriptionAnalyzerTests(unittest.TestCase):
    def test_parse_unsubscribe_metadata_extracts_targets(self) -> None:
        metadata = parse_unsubscribe_metadata(
            {
                "list-unsubscribe": (
                    "<mailto:leave@example.com>, "
                    "<https://example.com/unsubscribe>"
                ),
                "list-unsubscribe-post": "List-Unsubscribe=One-Click",
            }
        )

        self.assertEqual(metadata.mailto_links, ("mailto:leave@example.com",))
        self.assertEqual(metadata.web_links, ("https://example.com/unsubscribe",))
        self.assertTrue(metadata.supports_one_click)

    def test_marketing_sender_with_unsubscribe_metadata_is_unsubscribe_candidate(self) -> None:
        results = analyze_subscription_candidates(
            [
                message(
                    "newsletter@example.com",
                    "Weekly newsletter",
                    "Product updates and discount offers.",
                    {"list-unsubscribe": "<mailto:unsubscribe@example.com>"},
                ),
                message(
                    "newsletter@example.com",
                    "Monthly roundup",
                    "Recommended events and webinars.",
                    {"list-unsubscribe": "<mailto:unsubscribe@example.com>"},
                ),
            ]
        )

        self.assertEqual(len(results[UNSUBSCRIBE]), 1)
        self.assertEqual(results[UNSUBSCRIBE][0].sender_email, "newsletter@example.com")

    def test_transactional_sender_goes_to_human_review_even_with_metadata(self) -> None:
        results = analyze_subscription_candidates(
            [
                message(
                    "billing@example.com",
                    "Invoice receipt",
                    "Your payment receipt and invoice are ready.",
                    {"list-unsubscribe": "<mailto:unsubscribe@example.com>"},
                ),
                message(
                    "billing@example.com",
                    "Payment statement",
                    "Your billing statement is available.",
                    {"list-unsubscribe": "<mailto:unsubscribe@example.com>"},
                ),
            ]
        )

        self.assertEqual(len(results[UNSUBSCRIBE]), 0)
        self.assertEqual(len(results[HUMAN_REVIEW]), 1)

    def test_recurring_sender_without_metadata_is_keep_but_organize(self) -> None:
        results = analyze_subscription_candidates(
            [
                message("updates@example.com", "Weekly digest", "News and updates."),
                message("updates@example.com", "Monthly digest", "More product insights."),
            ]
        )

        self.assertEqual(len(results[KEEP_ORGANIZE]), 1)


if __name__ == "__main__":
    unittest.main()
