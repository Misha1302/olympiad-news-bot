import unittest
from datetime import datetime

from olympiad_news_bot.domain import IncomingMessage
from olympiad_news_bot.formatting import (
    TelegramNotificationFormatter,
    format_source,
    split_text_for_telegram,
)


class FormattingTests(unittest.TestCase):
    def test_source_link_is_created_for_public_channel(self) -> None:
        self.assertEqual(
            format_source("@channel", 42),
            "@channel: https://t.me/channel/42",
        )

    def test_split_prefers_boundary_and_never_exceeds_limit(self) -> None:
        parts = split_text_for_telegram("one two three", max_length=7)
        self.assertEqual("".join(parts), "one two three")
        self.assertTrue(all(len(part) <= 7 for part in parts))

    def test_formatter_preserves_original_message_text(self) -> None:
        formatter = TelegramNotificationFormatter(
            clock=lambda: datetime(2026, 7, 10, 12, 30)
        )
        notification = formatter.format(
            IncomingMessage(
                source_id="42",
                source_name="@channel",
                message_id=7,
                text="Original text 🚀",
            )
        )

        self.assertIn("Original text 🚀", notification.text)
        self.assertIn("12:30 10.07.2026", notification.text)
        self.assertEqual(notification.source_key, "42:7")
