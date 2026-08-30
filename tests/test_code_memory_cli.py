from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from migi.cli import main


class CodeMemoryCliTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, object]:
        output = io.StringIO()
        with patch("sys.argv", ["migi-genesis", *argv]), redirect_stdout(output):
            code = main()
        text = output.getvalue().strip()
        return code, json.loads(text) if text else None

    def test_import_recall_and_exact_find_across_cli_process_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db = root / "genesis.db"
            history = root / "conversation.md"
            history.write_text(
                """Discussion\n\n```python\ndef rag0shot_recall(query):\n    return query\n```\n""",
                encoding="utf-8",
            )

            code, imported = self._run(
                [
                    "--db",
                    str(db),
                    "code-import",
                    str(history),
                    "--source-kind",
                    "chat",
                    "--source-uri",
                    "chat:conversation-1",
                    "--conversation-id",
                    "conversation-1",
                    "--system",
                    "RAG0SHOT",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(imported["count"], 1)
            artifact = imported["artifacts"][0]
            self.assertEqual(artifact["language"], "python")

            code, recalled = self._run(
                [
                    "--db",
                    str(db),
                    "code-recall",
                    "rag0shot recall",
                    "--language",
                    "python",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(recalled["hits"]), 1)
            self.assertEqual(recalled["hits"][0]["artifact_id"], artifact["artifact_id"])
            self.assertEqual(recalled["hits"][0]["source"]["kind"], "chat")

            code, found = self._run(
                ["--db", str(db), "code-find", artifact["content_hash"]]
            )
            self.assertEqual(code, 0)
            self.assertEqual(found["artifact_id"], artifact["artifact_id"])


if __name__ == "__main__":
    unittest.main()
