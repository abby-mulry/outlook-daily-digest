from __future__ import annotations

import unittest

from gmail_subscription_cleanup.config import (
    GMAIL_READONLY_SCOPE,
    parse_scopes,
    validate_read_only_scopes,
)


class ConfigTests(unittest.TestCase):
    def test_parse_scopes_defaults_to_gmail_readonly(self) -> None:
        self.assertEqual(
            parse_scopes(None),
            (GMAIL_READONLY_SCOPE,),
        )

    def test_parse_scopes_accepts_gmail_readonly(self) -> None:
        self.assertEqual(
            parse_scopes(GMAIL_READONLY_SCOPE),
            (GMAIL_READONLY_SCOPE,),
        )

    def test_validate_read_only_scopes_rejects_mutating_gmail_scope(self) -> None:
        with self.assertRaisesRegex(ValueError, "read-only"):
            validate_read_only_scopes(("https://www.googleapis.com/auth/gmail.modify",))


if __name__ == "__main__":
    unittest.main()
