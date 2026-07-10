import unittest

from olympiad_news_bot.classification import (
    InvalidClassifierResponse,
    normalize_classifier_text,
    parse_binary_answer,
)


class ClassificationTests(unittest.TestCase):
    def test_accepts_only_exact_positive_and_negative_answers(self) -> None:
        self.assertTrue(parse_binary_answer("ДА"))
        self.assertTrue(parse_binary_answer("yes."))
        self.assertFalse(parse_binary_answer("НЕТ!"))
        self.assertFalse(parse_binary_answer("no"))

    def test_rejects_explanations_instead_of_guessing(self) -> None:
        with self.assertRaises(InvalidClassifierResponse):
            parse_binary_answer("Да, это олимпиада")

        with self.assertRaises(InvalidClassifierResponse):
            parse_binary_answer("Сообщение содержит слово олимпиада")

    def test_normalization_removes_control_characters_and_limits_length(self) -> None:
        self.assertEqual(normalize_classifier_text(" a\n\x00 b ", 3), "a b")
