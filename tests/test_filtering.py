import unittest

from olympiad_news_bot.filtering import KeywordPrefilter


class FilteringTests(unittest.TestCase):
    def test_relevant_olympiad_message_passes(self) -> None:
        self.assertTrue(
            KeywordPrefilter().matches(
                "Началась регистрация на олимпиаду по программированию"
            )
        )

    def test_short_or_unrelated_message_is_filtered(self) -> None:
        filter_ = KeywordPrefilter()
        self.assertFalse(filter_.matches("старт"))
        self.assertFalse(filter_.matches("Сегодня ожидается хорошая погода"))
