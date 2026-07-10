import asyncio
import unittest

from olympiad_news_bot.application import NewsProcessor
from olympiad_news_bot.domain import DeliveryReport, IncomingMessage, Notification
from olympiad_news_bot.queueing import MessageQueue
from olympiad_news_bot.runtime import BotRuntime


class FiniteSource:
    async def run(self, handler) -> None:
        await handler(
            IncomingMessage(
                source_id="42",
                source_name="@source",
                message_id=1,
                text="first olympiad message",
            )
        )
        await handler(
            IncomingMessage(
                source_id="42",
                source_name="@source",
                message_id=2,
                text="second olympiad message",
            )
        )


class PassFilter:
    def matches(self, text: str) -> bool:
        return True


class Formatter:
    def format(self, message: IncomingMessage) -> Notification:
        return Notification(message.source_key, message.text)


class RecordingSink:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def send(self, notification: Notification) -> DeliveryReport:
        await asyncio.sleep(0)
        self.keys.append(notification.source_key)
        return DeliveryReport(1, 1)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_drains_queue_before_shutdown(self) -> None:
        sink = RecordingSink()
        queue = MessageQueue(max_queue_size=1)
        runtime = BotRuntime(
            source=FiniteSource(),
            processor=NewsProcessor(PassFilter(), Formatter(), sink),
            queue=queue,
        )

        await runtime.run()

        self.assertEqual(sink.keys, ["42:1", "42:2"])
        self.assertEqual(queue.snapshot().delivered, 2)
        self.assertEqual(queue.snapshot().queue_size, 0)
