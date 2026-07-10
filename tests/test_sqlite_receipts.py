import tempfile
import unittest
from pathlib import Path

from olympiad_news_bot.adapters.sqlite_receipts import SqliteDeliveryReceiptStore


class SqliteReceiptTests(unittest.TestCase):
    def test_receipt_is_persistent_across_store_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipts.sqlite3"
            first = SqliteDeliveryReceiptStore(path)
            self.assertFalse(first.was_delivered("source:1", "chat", 0))
            first.mark_delivered("source:1", "chat", 0)

            second = SqliteDeliveryReceiptStore(path)
            self.assertTrue(second.was_delivered("source:1", "chat", 0))
