from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from gmail_subscription_cleanup.config import (
    GMAIL_READONLY_SCOPE,
    load_settings,
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

    def test_load_settings_resolves_oauth_files_next_to_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "GMAIL_CREDENTIALS_FILE=credentials.json",
                        "GMAIL_TOKEN_FILE=token.json",
                    ]
                ),
                encoding="utf-8",
            )
            old_values = {
                key: os.environ.pop(key, None)
                for key in (
                    "GMAIL_CREDENTIALS_FILE",
                    "GMAIL_TOKEN_FILE",
                    "GMAIL_SCOPES",
                )
            }

            try:
                settings = load_settings(env_path)
            finally:
                for key, value in old_values.items():
                    if value is not None:
                        os.environ[key] = value

            self.assertEqual(
                settings.credentials_path.resolve(),
                (Path(tmpdir) / "credentials.json").resolve(),
            )
            self.assertEqual(
                settings.token_path.resolve(),
                (Path(tmpdir) / "token.json").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
