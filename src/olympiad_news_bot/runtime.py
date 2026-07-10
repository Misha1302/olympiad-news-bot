from __future__ import annotations

import asyncio
import contextlib
import logging

from .application import NewsProcessor
from .ports import MessageSource
from .queueing import MessageQueue

LOGGER = logging.getLogger(__name__)


class BotRuntime:
    def __init__(
        self,
        source: MessageSource,
        processor: NewsProcessor,
        queue: MessageQueue,
    ) -> None:
        self._source = source
        self._processor = processor
        self._queue = queue

    async def run(self) -> None:
        worker = asyncio.create_task(self._worker(), name="message-worker")
        stats = asyncio.create_task(self._log_stats(), name="queue-stats")

        try:
            await self._source.run(self._queue.put)
        finally:
            await self._queue.join()
            worker.cancel()
            stats.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker
            with contextlib.suppress(asyncio.CancelledError):
                await stats
            LOGGER.info("Final queue stats: %s", self._queue.snapshot())

    async def _worker(self) -> None:
        while True:
            message = await self._queue.get()
            try:
                result = await self._processor.process(message)
                self._queue.mark_processed(result)
                LOGGER.info(
                    "Message %s processed with outcome %s",
                    message.source_key,
                    result.outcome.name,
                )
            except asyncio.CancelledError:
                self._queue.mark_processing_error()
                raise
            except Exception:
                self._queue.mark_processing_error()
                LOGGER.exception("Message %s processing failed", message.source_key)

    async def _log_stats(self) -> None:
        while True:
            await asyncio.sleep(30)
            LOGGER.info("Queue stats: %s", self._queue.snapshot())
