from __future__ import annotations

import unittest

from outlook_daily_digest.config import parse_scopes, validate_read_only_scopes


class ConfigTests(unittest.TestCase):
    def test_parse_scopes_accepts_spaces_and_commas(self) -> None:
        self.assertEqual(
            parse_scopes("User.Read, Mail.Read Calendars.Read"),
            ("User.Read", "Mail.Read", "Calendars.Read"),
        )

    def test_validate_read_only_scopes_rejects_mutating_permissions(self) -> None:
        with self.assertRaisesRegex(ValueError, "read-only"):
            validate_read_only_scopes(("User.Read", "Mail.Send"))


if __name__ == "__main__":
    unittest.main()
