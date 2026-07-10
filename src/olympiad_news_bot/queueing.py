from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .domain import IncomingMessage, ProcessingOutcome, ProcessingResult


@dataclass(frozen=True)
class QueueStatsSnapshot:
    accepted: int
    filtered_out: int
    irrelevant: int
    classifier_unavailable: int
    delivered: int
    partially_delivered: int
    delivery_failed: int
    processing_errors: int
    queue_size: int


class MessageQueue:
    def __init__(self, max_queue_size: int = 100) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")
        self._queue: asyncio.Queue[IncomingMessage] = asyncio.Queue(maxsize=max_queue_size)
        self._counts = {
            "accepted": 0,
            "filtered_out": 0,
            "irrelevant": 0,
            "classifier_unavailable": 0,
            "delivered": 0,
            "partially_delivered": 0,
            "delivery_failed": 0,
            "processing_errors": 0,
        }

    async def put(self, message: IncomingMessage) -> None:
        await self._queue.put(message)
        self._counts["accepted"] += 1

    async def get(self) -> IncomingMessage:
        return await self._queue.get()

    async def join(self) -> None:
        await self._queue.join()

    def mark_processed(self, result: ProcessingResult) -> None:
        mapping = {
            ProcessingOutcome.FILTERED_OUT: "filtered_out",
            ProcessingOutcome.IRRELEVANT: "irrelevant",
            ProcessingOutcome.CLASSIFIER_UNAVAILABLE: "classifier_unavailable",
            ProcessingOutcome.DELIVERED: "delivered",
            ProcessingOutcome.PARTIALLY_DELIVERED: "partially_delivered",
            ProcessingOutcome.DELIVERY_FAILED: "delivery_failed",
        }
        self._counts[mapping[result.outcome]] += 1
        self._queue.task_done()

    def mark_processing_error(self) -> None:
        self._counts["processing_errors"] += 1
        self._queue.task_done()

    def snapshot(self) -> QueueStatsSnapshot:
        return QueueStatsSnapshot(
            **self._counts,
            queue_size=self._queue.qsize(),
        )
