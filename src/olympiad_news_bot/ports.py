from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from .domain import ClassificationDecision, DeliveryReport, IncomingMessage, Notification


class MessagePrefilter(Protocol):
    def matches(self, text: str) -> bool:
        ...


class MessageClassifier(Protocol):
    async def classify(self, text: str) -> ClassificationDecision:
        ...


class NotificationFormatter(Protocol):
    def format(self, message: IncomingMessage) -> Notification:
        ...


class NotificationSink(Protocol):
    async def send(self, notification: Notification) -> DeliveryReport:
        ...


MessageHandler = Callable[[IncomingMessage], Awaitable[None]]


class MessageSource(Protocol):
    async def run(self, handler: MessageHandler) -> None:
        ...
