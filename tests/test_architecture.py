import ast
import unittest
from pathlib import Path


class ArchitectureFitnessTests(unittest.TestCase):
    def test_application_layer_does_not_depend_on_external_adapters(self) -> None:
        source_path = (
            Path(__file__).parents[1]
            / "src"
            / "olympiad_news_bot"
            / "application.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        forbidden_roots = {"requests", "telebot", "telethon", "urllib3"}
        imported_roots: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

        self.assertTrue(forbidden_roots.isdisjoint(imported_roots))
