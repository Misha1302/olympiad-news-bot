import unittest

from olympiad_news_bot.delivery import TelegramNotificationSink
from olympiad_news_bot.domain import Notification


class FlakyBot:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.failures_remaining = 1

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        disable_web_page_preview: bool,
    ) -> object:
        self.calls.append((chat_id, text))
        if text.startswith("B") and self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("temporary failure")
        return object()


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_is_scoped_to_failed_part_and_does_not_duplicate_success(self) -> None:
        bot = FlakyBot()
        sink = TelegramNotificationSink(
            bot=bot,
            chat_ids=("chat",),
            max_retries=2,
            sleep=lambda _: None,
        )
        notification = Notification("source:1", "A" * 4096 + "B")

        report = await sink.send(notification)

        self.assertTrue(report.succeeded)
        self.assertEqual(report.attempted, 2)
        self.assertEqual(report.delivered, 2)
        first_part_calls = [call for call in bot.calls if call[1].startswith("A")]
        second_part_calls = [call for call in bot.calls if call[1].startswith("B")]
        self.assertEqual(len(first_part_calls), 1)
        self.assertEqual(len(second_part_calls), 2)

    async def test_reports_partial_delivery_per_destination(self) -> None:
        class SelectivelyFailingBot:
            def send_message(self, chat_id: str, text: str, **_: object) -> object:
                if chat_id == "bad":
                    raise RuntimeError("permanent")
                return object()

        sink = TelegramNotificationSink(
            SelectivelyFailingBot(),
            ("good", "bad"),
            max_retries=1,
        )
        report = await sink.send(Notification("source:1", "message"))

        self.assertTrue(report.partially_succeeded)
        self.assertEqual(report.delivered, 1)
        self.assertEqual(report.failures[0].chat_id, "bad")


class ReceiptStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_recorded_delivery_is_not_sent_again(self) -> None:
        class RecordingBot:
            def __init__(self) -> None:
                self.calls = 0

            def send_message(self, chat_id: str, text: str, **_: object) -> object:
                self.calls += 1
                return object()

        class MemoryStore:
            def __init__(self) -> None:
                self.keys: set[tuple[str, str, int]] = set()

            def was_delivered(
                self,
                source_key: str,
                chat_id: str,
                part_index: int,
            ) -> bool:
                return (source_key, chat_id, part_index) in self.keys

            def mark_delivered(
                self,
                source_key: str,
                chat_id: str,
                part_index: int,
            ) -> None:
                self.keys.add((source_key, chat_id, part_index))

        bot = RecordingBot()
        store = MemoryStore()
        sink = TelegramNotificationSink(
            bot=bot,
            chat_ids=("chat",),
            receipt_store=store,
        )
        notification = Notification("stable-source:7", "message")

        first = await sink.send(notification)
        second = await sink.send(notification)

        self.assertTrue(first.succeeded)
        self.assertTrue(second.succeeded)
        self.assertEqual(bot.calls, 1)


class OrderingTests(unittest.IsolatedAsyncioTestCase):
    async def test_permanent_failure_stops_later_parts_for_same_chat(self) -> None:
        class FirstPartFailingBot:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def send_message(self, chat_id: str, text: str, **_: object) -> object:
                self.calls.append(text)
                raise RuntimeError("permanent")

        bot = FirstPartFailingBot()
        sink = TelegramNotificationSink(bot, ("chat",), max_retries=1)

        report = await sink.send(Notification("source:1", "A" * 4096 + "B"))

        self.assertFalse(report.succeeded)
        self.assertEqual(report.delivered, 0)
        self.assertEqual(len(bot.calls), 1)
        self.assertEqual(report.failures[0].part_index, 0)
