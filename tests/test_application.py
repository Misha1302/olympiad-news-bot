import unittest

from olympiad_news_bot.application import NewsProcessor
from olympiad_news_bot.domain import (
    ClassificationDecision,
    DeliveryFailure,
    DeliveryReport,
    IncomingMessage,
    Notification,
    ProcessingOutcome,
)


class AlwaysPass:
    def matches(self, text: str) -> bool:
        return True


class AlwaysFail:
    def matches(self, text: str) -> bool:
        return False


class FixedClassifier:
    def __init__(self, decision: ClassificationDecision) -> None:
        self.decision = decision

    async def classify(self, text: str) -> ClassificationDecision:
        return self.decision


class Formatter:
    def format(self, message: IncomingMessage) -> Notification:
        return Notification(message.source_key, message.text)


class FixedSink:
    def __init__(self, report: DeliveryReport) -> None:
        self.report = report
        self.calls = 0

    async def send(self, notification: Notification) -> DeliveryReport:
        self.calls += 1
        return self.report


def incoming_message() -> IncomingMessage:
    return IncomingMessage(
        source_id="42",
        source_name="@source",
        message_id=1,
        text="text",
    )


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefilter_stops_external_classification_and_delivery(self) -> None:
        sink = FixedSink(DeliveryReport(1, 1))
        processor = NewsProcessor(AlwaysFail(), Formatter(), sink)

        result = await processor.process(incoming_message())

        self.assertEqual(result.outcome, ProcessingOutcome.FILTERED_OUT)
        self.assertEqual(sink.calls, 0)

    async def test_fail_closed_does_not_deliver_when_classifier_is_unavailable(self) -> None:
        sink = FixedSink(DeliveryReport(1, 1))
        processor = NewsProcessor(
            AlwaysPass(),
            Formatter(),
            sink,
            FixedClassifier(ClassificationDecision.UNAVAILABLE),
            fail_open=False,
        )

        result = await processor.process(incoming_message())

        self.assertEqual(result.outcome, ProcessingOutcome.CLASSIFIER_UNAVAILABLE)
        self.assertEqual(sink.calls, 0)

    async def test_partial_delivery_is_not_reported_as_success(self) -> None:
        report = DeliveryReport(
            attempted=2,
            delivered=1,
            failures=(DeliveryFailure("chat", 1, "failed"),),
        )
        processor = NewsProcessor(
            AlwaysPass(),
            Formatter(),
            FixedSink(report),
        )

        result = await processor.process(incoming_message())

        self.assertEqual(result.outcome, ProcessingOutcome.PARTIALLY_DELIVERED)
