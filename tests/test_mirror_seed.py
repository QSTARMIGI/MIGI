from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from migi.canonical import chained_hash, sha256_hex
from migi.mirror_seed import MirrorSeed, verify_bundle


class MirrorSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "private-note.txt"
        self.original = b"MIGI first capture\nTwo lines.\n"
        self.path.write_bytes(self.original)
        self.db = self.root / "genesis.db"
        self.mirror = MirrorSeed(self.db, allowed_roots=[self.root])

    def capture(self):
        return self.mirror.capture(self.path, consent_scope="local.capture")

    def flow(self, include_original=False):
        captured = self.capture()
        derived = self.mirror.analyze(captured["artifact"]["artifact_id"], consent_scope="local.analyze")
        exported = self.mirror.export(derived["artifact"]["artifact_id"], consent_scope="local.export",
                                      include_original=include_original)
        return captured, derived, exported

    def test_end_to_end_survives_restart_and_source_deletion(self):
        capture = self.capture()
        self.path.unlink()
        self.mirror = MirrorSeed(self.db, allowed_roots=[self.root])
        derived = self.mirror.analyze(capture["artifact"]["artifact_id"], consent_scope="local.analyze")
        output = self.mirror.export(derived["artifact"]["artifact_id"], consent_scope="local.export", include_original=True)
        verification = verify_bundle(output["bundle"], expected_export_hash=output["receipt_hash"])
        self.assertTrue(verification["valid"])
        self.assertTrue(verification["analysis_replayed"])
        self.assertFalse(verification["identity_verified"])
        original = output["bundle"]["manifest"]["payloads"][capture["artifact"]["artifact_id"]]
        self.assertEqual(base64.b64decode(original), self.original)
        history = self.mirror.history(derived["artifact"]["artifact_id"])
        self.assertEqual(history["parent"]["artifact"]["artifact_id"], capture["artifact"]["artifact_id"])
        self.assertEqual(history["chain"]["checked"], 3)

    def test_scopes_are_separate_and_default_to_hold(self):
        with patch.object(Path, "open", side_effect=AssertionError("must not read")):
            held = self.mirror.capture(self.path)
        self.assertEqual(held["authority"]["tre_logic"], "0")
        captured = self.capture()
        reference = captured["artifact"]["artifact_id"]
        with patch.object(self.mirror, "_verified_asset", side_effect=AssertionError("must not access")):
            for result in [self.mirror.analyze(reference, consent_scope="local.capture"),
                           self.mirror.export(reference, consent_scope="local.analyze")]:
                self.assertIsNone(result["execution"])
                self.assertEqual(result["authority"]["tre_logic"], "0")
        self.assertEqual(len(self.mirror.store.list_kind("mirror_artifact")), 1)

    def test_capture_outside_root_and_symlink_escape_are_denied(self):
        with tempfile.TemporaryDirectory() as other:
            target = Path(other) / "secret"
            target.write_bytes(b"secret")
            link = self.root / "link"
            link.symlink_to(target)
            for path in (target, link):
                result = self.mirror.capture(path, consent_scope="local.capture")
                self.assertEqual(result["authority"]["tre_logic"], "-1")
                self.assertIsNone(result["artifact"])

    def test_export_omits_original_paths_and_unrelated_history(self):
        private = self.capture()
        _, derived, exported = self.flow()
        bundle = exported["bundle"]
        self.assertEqual(set(bundle["manifest"]["payloads"]), {derived["artifact"]["artifact_id"]})
        encoded = json.dumps(bundle)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn(self.path.name, encoded)
        self.assertNotIn(private["receipt"]["receipt_id"], encoded)
        result = verify_bundle(bundle)
        self.assertTrue(result["valid"])
        self.assertFalse(result["analysis_replayed"])
        self.assertFalse(result["original_included"])

    def test_tampering_in_manifest_receipts_payloads_and_anchor_fails(self):
        _, derived, exported = self.flow(True)
        pristine = exported["bundle"]
        mutations = [
            lambda b: b["manifest"]["derived"].update(source_class="original"),
            lambda b: b["manifest"]["history"][0]["receipt"]["authority"].update(tre_logic="-1"),
            lambda b: b["manifest"]["payloads"].update({derived["artifact"]["artifact_id"]: "YWJj"}),
            lambda b: b["manifest"].update(include_original=False),
            lambda b: b["manifest"]["derived"].update(parent_artifact_id="different"),
        ]
        for mutate in mutations:
            altered = deepcopy(pristine)
            mutate(altered)
            self.assertFalse(verify_bundle(altered)["valid"])
        self.assertFalse(verify_bundle(pristine, expected_export_hash="0" * 64)["valid"])
        # Rehashing the outer manifest cannot conceal invalid inner payloads.
        altered = deepcopy(pristine)
        altered["manifest"]["payloads"][derived["artifact"]["artifact_id"]] = "YWJj"
        from migi.canonical import canonical_json_bytes
        receipt = altered["export_receipt"]["receipt"]
        receipt["metadata"]["bundle_digest"] = sha256_hex(canonical_json_bytes(altered["manifest"]))
        altered["export_receipt"]["receipt_hash"] = chained_hash(receipt["previous_receipt_ref"], receipt)
        self.assertFalse(verify_bundle(altered)["valid"])

    def test_malformed_bundles_fail_closed(self):
        for value in (None, [], {}, {"manifest": {}}, {"manifest": {"schema_version": "wrong"}}):
            self.assertFalse(verify_bundle(value)["valid"])

    def test_modified_stored_bytes_block_analysis(self):
        captured = self.capture()
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE artifact_bytes SET data = ?", (b"changed",))
        result = self.mirror.analyze(captured["artifact"]["artifact_id"], consent_scope="local.analyze")
        self.assertFalse(result["execution"]["success"])
        self.assertIsNone(result["artifact"])
        self.assertTrue(self.mirror.store.verify_chain()["valid"])

    def test_modified_descriptor_blocks_analysis(self):
        captured = self.capture()
        ref = captured["artifact"]["artifact_id"]
        with closing(sqlite3.connect(self.db)) as conn, conn:
            record = dict(captured["artifact"], media_type="changed/type")
            conn.execute("UPDATE objects SET payload_json = ? WHERE object_id = ?", (json.dumps(record), ref))
        result = self.mirror.analyze(ref, consent_scope="local.analyze")
        self.assertFalse(result["execution"]["success"])
        self.assertEqual(result["receipt"]["metadata"]["error"], "artifact_receipt_mismatch")

    def test_binary_and_oversize_inputs_have_no_successful_derivative(self):
        self.path.write_bytes(b"\xff\xfe")
        capture = self.capture()
        result = self.mirror.analyze(capture["artifact"]["artifact_id"], consent_scope="local.analyze")
        self.assertFalse(result["execution"]["success"])
        self.assertEqual(result["receipt"]["metadata"]["error"], "input_not_utf8")
        with patch("migi.mirror_seed.MAX_CAPTURE_BYTES", 1):
            result = self.capture()
        self.assertFalse(result["execution"]["success"])
        self.assertEqual(len(self.mirror.store.list_kind("mirror_artifact")), 1)

    def test_atomic_rollback_leaves_no_orphan_blob_or_receipt(self):
        captured = self.capture()
        receipt = captured["receipt"]
        from migi.models import MIGIReceipt
        before = self.mirror.store.verify_chain()
        existing = captured["artifact"]
        with self.assertRaises(sqlite3.IntegrityError):
            self.mirror.store.commit_operation(MIGIReceipt(**receipt), [
                ("mirror_artifact", existing["artifact_id"], existing["created_at"], existing)
            ], [b"orphan"])
        self.assertEqual(before, self.mirror.store.verify_chain())
        with self.assertRaises(ValueError):
            self.mirror.store.artifact_data(sha256_hex(b"orphan"))

    def test_concurrent_captures_serialize_receipt_head(self):
        def capture(_):
            return MirrorSeed(self.db, allowed_roots=[self.root]).capture(self.path, consent_scope="local.capture")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(capture, range(8)))
        self.assertTrue(all(r["execution"]["success"] for r in results))
        self.assertEqual(self.mirror.store.verify_chain()["checked"], 8)
        self.assertTrue(self.mirror.store.verify_chain()["valid"])

    def test_cli_round_trip_and_standalone_verifier(self):
        def cli(*args):
            process = subprocess.run([sys.executable, "-m", "migi.cli", "--db", str(self.db), *args],
                                     capture_output=True, text=True)
            return process.returncode, json.loads(process.stdout)
        code, capture = cli("mirror-capture", str(self.path), "--scope", "local.capture")
        self.assertEqual(code, 0)
        code, derived = cli("mirror-analyze", capture["artifact"]["artifact_id"], "--scope", "local.analyze")
        self.assertEqual(code, 0)
        output = self.root / "bundle.json"
        code, exported = cli("mirror-export", derived["artifact"]["artifact_id"], str(output), "--scope", "local.export", "--include-original")
        self.assertEqual(code, 0)
        output_bytes = output.read_bytes()
        code, _ = cli("mirror-export", derived["artifact"]["artifact_id"], str(output), "--scope", "local.export")
        self.assertEqual(code, 1)
        self.assertEqual(output_bytes, output.read_bytes())
        self.db.unlink()
        code, result = cli("mirror-verify", str(output), "--expected-export-hash", exported["receipt_hash"])
        self.assertEqual(code, 0)
        self.assertTrue(result["analysis_replayed"])
        self.assertFalse(self.db.exists())
        output.write_text("{}")
        code, result = cli("mirror-verify", str(output))
        self.assertEqual(code, 1)
        self.assertFalse(result["valid"])
