import asyncio
import unittest

from olympiad_news_bot.domain import IncomingMessage, ProcessingOutcome, ProcessingResult
from olympiad_news_bot.queueing import MessageQueue


def message(message_id: int, text: str) -> IncomingMessage:
    return IncomingMessage(
        source_id="a",
        source_name="a",
        message_id=message_id,
        text=text,
    )


class QueueingTests(unittest.IsolatedAsyncioTestCase):
    async def test_put_applies_backpressure_instead_of_dropping_message(self) -> None:
        queue = MessageQueue(max_queue_size=1)
        await queue.put(message(1, "first"))
        blocked_put = asyncio.create_task(queue.put(message(2, "second")))
        await asyncio.sleep(0)
        self.assertFalse(blocked_put.done())

        await queue.get()
        queue.mark_processed(ProcessingResult(ProcessingOutcome.FILTERED_OUT))
        await blocked_put

        self.assertEqual(queue.snapshot().accepted, 2)
