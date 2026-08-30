from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from migi.code_memory import CodeMemory, CodeSource
from migi.storage import GenesisStore


class CodeMemoryTests(unittest.TestCase):
    def test_imports_polyglot_chat_code_and_recalls_with_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = GenesisStore(Path(temp_dir) / "genesis.db")
            memory = CodeMemory(store)
            source = CodeSource(
                kind="chat",
                uri="chat:migi-history",
                conversation_id="conv-1",
                message_id="msg-7",
            )
            text = """
```python
def recall(query):
    return query
```

```c++
void on_can_frame() {}
```
"""
            artifacts = memory.import_fenced_text(
                text,
                source=source,
                named_systems=["RAG0SHOT", "CAMbus"],
                tags=["recall", "network"],
            )

            self.assertEqual(len(artifacts), 2)
            self.assertEqual(artifacts[0]["language"], "python")
            self.assertEqual(artifacts[1]["language"], "cpp")
            self.assertTrue(artifacts[0]["content_hash"].startswith("sha256:"))

            hits = memory.recall("recall python", languages=["python"])
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["source"]["kind"], "chat")
            self.assertEqual(hits[0]["source"]["conversation_id"], "conv-1")

    def test_deduplicates_identical_content_by_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = GenesisStore(Path(temp_dir) / "genesis.db")
            memory = CodeMemory(store)
            source = CodeSource(kind="log", uri="log:one")
            text = """```rust
fn main() { println!(\"MIGI\"); }
```"""

            first = memory.import_fenced_text(text, source=source)
            second = memory.import_fenced_text(text, source=source)

            self.assertEqual(first[0]["artifact_id"], second[0]["artifact_id"])
            self.assertEqual(len(store.list_kind("code_artifact")), 1)

    def test_exact_hash_lookup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = GenesisStore(Path(temp_dir) / "genesis.db")
            memory = CodeMemory(store)
            artifact = memory.import_fenced_text(
                """```tre-logic
+1 proceed
```""",
                source=CodeSource(kind="file", uri="file:rules.md"),
                status="specification",
            )[0]

            found = memory.find_exact(artifact["content_hash"])
            self.assertIsNotNone(found)
            self.assertEqual(found["language"], "tre-logic")


if __name__ == "__main__":
    unittest.main()
