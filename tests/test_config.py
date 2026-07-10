import unittest

from olympiad_news_bot.config import ConfigurationError, settings_from_mapping


BASE_CONFIG = {
    "TELEGRAM_API_ID": "123",
    "TELEGRAM_API_HASH": "hash",
    "TELEGRAM_BOT_TOKEN": "token",
    "IDS_TO_CHAT": "1, 2",
    "GIGACHAT_ENABLED": "false",
}


class ConfigTests(unittest.TestCase):
    def test_builds_typed_settings_without_gigachat_key_when_disabled(self) -> None:
        settings = settings_from_mapping(BASE_CONFIG)

        self.assertEqual(settings.telegram.api_id, 123)
        self.assertEqual(settings.telegram.destination_chat_ids, ("1", "2"))
        self.assertFalse(settings.gigachat.enabled)
        self.assertGreater(len(settings.telegram.monitor_channels), 0)

    def test_requires_gigachat_key_when_enabled(self) -> None:
        values = {**BASE_CONFIG, "GIGACHAT_ENABLED": "true"}
        with self.assertRaises(ConfigurationError):
            settings_from_mapping(values)

    def test_rejects_invalid_boolean_instead_of_silently_disabling(self) -> None:
        values = {**BASE_CONFIG, "GIGACHAT_ENABLED": "maybe"}
        with self.assertRaises(ConfigurationError):
            settings_from_mapping(values)

    def test_rejects_non_positive_retry_count(self) -> None:
        values = {**BASE_CONFIG, "TELEGRAM_SEND_MAX_RETRIES": "0"}
        with self.assertRaises(ConfigurationError):
            settings_from_mapping(values)
