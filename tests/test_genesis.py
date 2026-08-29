from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from migi.genesis import GenesisNode


class GenesisNodeTests(unittest.TestCase):
    def test_end_to_end_receipt_memory_recall(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_path = root / "sample.txt"
            artifact_path.write_text("MIGI Genesis\n", encoding="utf-8")
            node = GenesisNode(root / "genesis.db", allowed_roots=[root])

            result = node.inspect_artifact(artifact_path, actor_id="tester")

            self.assertEqual(result["authority"]["tre_logic"], "+1")
            self.assertTrue(result["execution"]["success"])
            self.assertTrue(result["execution"]["verification"]["sha256_match"])
            self.assertTrue(result["execution"]["verification"]["size_match"])
            self.assertEqual(result["receipt"]["output_ref"], result["artifact"]["artifact_id"])

            chain = node.store.verify_chain()
            self.assertTrue(chain["valid"])
            self.assertEqual(chain["checked"], 1)

            recalled = node.recall_artifact(result["artifact"]["sha256"])
            self.assertIsNotNone(recalled)
            self.assertEqual(recalled["artifact"]["artifact_id"], result["artifact"]["artifact_id"])
            self.assertEqual(recalled["history"][0]["intent"]["action"], "artifact.inspect")
            self.assertEqual(
                recalled["history"][0]["execution"]["execution_id"],
                result["execution"]["execution_id"],
            )

    def test_unapproved_scope_holds_and_does_not_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_path = root / "sample.txt"
            artifact_path.write_text("private", encoding="utf-8")
            node = GenesisNode(root / "genesis.db", allowed_roots=[root])

            result = node.inspect_artifact(artifact_path, consent_scope="unspecified")

            self.assertEqual(result["authority"]["tre_logic"], "0")
            self.assertIsNone(result["execution"])
            self.assertIsNone(result["artifact"])
            self.assertEqual(node.store.verify_chain()["checked"], 1)

    def test_target_outside_root_is_denied(self):
        with tempfile.TemporaryDirectory() as allowed_dir, tempfile.TemporaryDirectory() as other_dir:
            allowed = Path(allowed_dir)
            target = Path(other_dir) / "outside.txt"
            target.write_text("outside", encoding="utf-8")
            node = GenesisNode(allowed / "genesis.db", allowed_roots=[allowed])

            result = node.inspect_artifact(target)

            self.assertEqual(result["authority"]["tre_logic"], "-1")
            self.assertEqual(result["authority"]["reason_code"], "policy.target_outside_allowed_root")
            self.assertIsNone(result["execution"])

    def test_second_receipt_links_to_first_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "one.txt"
            second = root / "two.txt"
            first.write_text("one", encoding="utf-8")
            second.write_text("two", encoding="utf-8")
            node = GenesisNode(root / "genesis.db", allowed_roots=[root])

            r1 = node.inspect_artifact(first)
            r2 = node.inspect_artifact(second)

            self.assertEqual(r2["receipt"]["previous_receipt_ref"], r1["receipt_hash"])
            verification = node.store.verify_chain()
            self.assertTrue(verification["valid"])
            self.assertEqual(verification["checked"], 2)


if __name__ == "__main__":
    unittest.main()
