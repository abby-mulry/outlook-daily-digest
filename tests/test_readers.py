from __future__ import annotations

import unittest

from gmail_subscription_cleanup.inbox_reader import GmailInboxReader, message_from_gmail


class FakeRequest:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def execute(self) -> dict:
        return self.payload


class FakeMessages:
    def __init__(self) -> None:
        self.list_calls: list[dict] = []
        self.get_calls: list[dict] = []

    def list(self, **kwargs) -> FakeRequest:
        self.list_calls.append(kwargs)
        return FakeRequest({"messages": [{"id": "message-1"}]})

    def get(self, **kwargs) -> FakeRequest:
        self.get_calls.append(kwargs)
        return FakeRequest(
            {
                "id": kwargs["id"],
                "threadId": "thread-1",
                "snippet": "Weekly product updates.",
                "labelIds": ["INBOX"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": "News <news@example.com>"},
                        {"name": "Subject", "value": "Weekly newsletter"},
                        {
                            "name": "List-Unsubscribe",
                            "value": "<mailto:leave@example.com>",
                        },
                    ]
                },
            }
        )


class FakeUsers:
    def __init__(self, messages: FakeMessages) -> None:
        self._messages = messages

    def messages(self) -> FakeMessages:
        return self._messages


class FakeGmailService:
    def __init__(self) -> None:
        self.messages = FakeMessages()

    def users(self) -> FakeUsers:
        return FakeUsers(self.messages)


class ReaderTests(unittest.TestCase):
    def test_inbox_reader_reads_gmail_inbox_metadata(self) -> None:
        service = FakeGmailService()
        messages = GmailInboxReader(service).list_messages(
            max_results=1,
            query="newer_than:90d",
        )

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender_email, "news@example.com")
        self.assertEqual(messages[0].headers["list-unsubscribe"], "<mailto:leave@example.com>")
        self.assertEqual(service.messages.list_calls[0]["labelIds"], ["INBOX"])
        self.assertEqual(service.messages.list_calls[0]["q"], "newer_than:90d")
        self.assertEqual(service.messages.get_calls[0]["format"], "metadata")
        self.assertIn(
            "List-Unsubscribe",
            service.messages.get_calls[0]["metadataHeaders"],
        )

    def test_message_from_gmail_uses_internal_date_fallback(self) -> None:
        message = message_from_gmail(
            {
                "id": "message-1",
                "threadId": "thread-1",
                "internalDate": "1780000000000",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Sender <sender@example.com>"},
                        {"name": "Subject", "value": "Hello"},
                    ]
                },
            }
        )

        self.assertEqual(message.sender_email, "sender@example.com")
        self.assertTrue(message.received_at.startswith("2026-"))


if __name__ == "__main__":
    unittest.main()
