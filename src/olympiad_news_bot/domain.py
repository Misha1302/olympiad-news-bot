from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto


@dataclass(frozen=True)
class IncomingMessage:
    source_id: str
    source_name: str
    message_id: int
    text: str
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def source_key(self) -> str:
        return f"{self.source_id}:{self.message_id}"


@dataclass(frozen=True)
class Notification:
    source_key: str
    text: str


class ClassificationDecision(Enum):
    RELEVANT = auto()
    IRRELEVANT = auto()
    UNAVAILABLE = auto()


@dataclass(frozen=True)
class DeliveryFailure:
    chat_id: str
    part_index: int
    error: str


@dataclass(frozen=True)
class DeliveryReport:
    attempted: int
    delivered: int
    failures: tuple[DeliveryFailure, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.attempted > 0 and self.delivered == self.attempted

    @property
    def partially_succeeded(self) -> bool:
        return 0 < self.delivered < self.attempted


class ProcessingOutcome(Enum):
    FILTERED_OUT = auto()
    IRRELEVANT = auto()
    CLASSIFIER_UNAVAILABLE = auto()
    DELIVERED = auto()
    PARTIALLY_DELIVERED = auto()
    DELIVERY_FAILED = auto()


@dataclass(frozen=True)
class ProcessingResult:
    outcome: ProcessingOutcome
    delivery: DeliveryReport | None = None
