from __future__ import annotations

from .domain import (
    ClassificationDecision,
    IncomingMessage,
    ProcessingOutcome,
    ProcessingResult,
)
from .ports import MessageClassifier, MessagePrefilter, NotificationFormatter, NotificationSink


class NewsProcessor:
    def __init__(
        self,
        prefilter: MessagePrefilter,
        formatter: NotificationFormatter,
        sink: NotificationSink,
        classifier: MessageClassifier | None = None,
        fail_open: bool = True,
    ) -> None:
        self._prefilter = prefilter
        self._classifier = classifier
        self._formatter = formatter
        self._sink = sink
        self._fail_open = fail_open

    async def process(self, message: IncomingMessage) -> ProcessingResult:
        if not self._prefilter.matches(message.text):
            return ProcessingResult(ProcessingOutcome.FILTERED_OUT)

        decision = ClassificationDecision.RELEVANT
        if self._classifier is not None:
            decision = await self._classifier.classify(message.text)

        if decision is ClassificationDecision.IRRELEVANT:
            return ProcessingResult(ProcessingOutcome.IRRELEVANT)

        if decision is ClassificationDecision.UNAVAILABLE and not self._fail_open:
            return ProcessingResult(ProcessingOutcome.CLASSIFIER_UNAVAILABLE)

        notification = self._formatter.format(message)
        delivery = await self._sink.send(notification)

        if delivery.succeeded:
            outcome = ProcessingOutcome.DELIVERED
        elif delivery.partially_succeeded:
            outcome = ProcessingOutcome.PARTIALLY_DELIVERED
        else:
            outcome = ProcessingOutcome.DELIVERY_FAILED

        return ProcessingResult(outcome=outcome, delivery=delivery)
