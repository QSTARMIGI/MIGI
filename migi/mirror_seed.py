"""MIRROR SEED MS-001: offline selected-file capture, analysis, and export.

Integrity receipts are unsigned. An original is the imported byte sequence, not
proof of sensor origin, authorship, wall-clock accuracy, or external truth.
"""
from __future__ import annotations

import base64
import binascii
import mimetypes
from pathlib import Path
from typing import Any

from .canonical import canonical_json_bytes, chained_hash, sha256_hex
from .genesis import GenesisNode
from .models import MIGIExecution, MIGIIntent, MIGIMemory, MIGIReceipt
from .util import new_id, utc_now

MAX_CAPTURE_BYTES = 8 * 1024 * 1024
ADAPTER = "migi.text-stats.v1"
BUNDLE_SCHEMA = "migi-mirror-bundle.v1"


def text_analysis(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="strict")
    return canonical_json_bytes({
        "adapter": ADAPTER, "source_class": "derived",
        "input_sha256": sha256_hex(data), "bytes": len(data),
        "characters": len(text), "words": len(text.split()),
        "lines": len(text.splitlines()),
    })


def _hash(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))


def _entry(receipt: dict) -> dict:
    return {"receipt": {k: v for k, v in receipt.items()
                        if k not in {"sequence", "receipt_hash", "previous_receipt_hash"}},
            "receipt_hash": receipt["receipt_hash"]}


class MirrorSeed:
    def __init__(self, db_path: str | Path, *, allowed_roots=None):
        self.node = GenesisNode(db_path, allowed_roots=allowed_roots)
        self.store = self.node.store

    def _authorize(self, action, target, scope, actor):
        intent = MIGIIntent(new_id("intent"), utc_now(), actor, action, target, scope)
        return intent, self.node.guard.evaluate(intent).authority

    def _record(self, intent, authority, *, artifact=None, data=None, metadata=None, error=None):
        allowed = authority.tre_logic == "+1"
        successful = allowed and error is None
        now = utc_now()
        execution = None
        if allowed:
            execution = MIGIExecution(
                new_id("exec"), now, now, intent.intent_id, authority.authority_id,
                "migi.mirror_seed", intent.action, successful,
                {"artifact_id": artifact["artifact_id"]} if artifact else {},
                {"verified": successful, **({"error": error} if error else {})},
            )
        receipt_metadata = {"operation": intent.action, "verified": successful,
                            "executed": allowed, **(metadata or {})}
        if execution:
            receipt_metadata["execution_ref"] = execution.execution_id
        if artifact:
            receipt_metadata["artifact_digest"] = _hash(artifact)
        if error:
            receipt_metadata["error"] = error
        receipt = MIGIReceipt(
            "migi-receipt.v0", new_id("receipt"), now,
            execution.execution_id if execution else authority.authority_id,
            artifact["source_class"] if artifact else ("authorized" if successful else "proposed"),
            intent.intent_id, artifact["artifact_id"] if artifact else authority.authority_id, "",
            {"tre_logic": authority.tre_logic, "reason_code": authority.reason_code,
             "consent_scope": authority.consent_scope}, receipt_metadata,
        )
        memory = MIGIMemory(new_id("memory"), now,
                            artifact["artifact_id"] if artifact else intent.intent_id,
                            receipt.receipt_id, intent.action,
                            f"{intent.action}: {'completed' if successful else 'not completed'}",
                            {"verified": successful, "authority_ref": authority.authority_id})
        objects = [("intent", intent.intent_id, now, intent.to_dict()),
                   ("authority", authority.authority_id, now, authority.to_dict()),
                   ("memory", memory.memory_id, now, memory.to_dict())]
        if execution:
            objects.append(("execution", execution.execution_id, now, execution.to_dict()))
        if artifact:
            objects.append(("mirror_artifact", artifact["artifact_id"], now, artifact))
        receipt, digest = self.store.commit_operation(receipt, objects, [data] if data is not None else [])
        return {"authority": authority.to_dict(), "execution": execution.to_dict() if execution else None,
                "artifact": artifact, "receipt": receipt.to_dict(), "receipt_hash": digest}

    def capture(self, path, *, consent_scope="", actor_id="local-user"):
        target = Path(path).expanduser().resolve()
        intent, authority = self._authorize("artifact.capture", str(target), consent_scope, actor_id)
        if authority.tre_logic != "+1":
            return self._record(intent, authority)
        try:
            if not self.store.verify_chain()["valid"]:
                raise ValueError("invalid_receipt_chain")
            with target.open("rb") as stream:
                data = stream.read(MAX_CAPTURE_BYTES + 1)
            if len(data) > MAX_CAPTURE_BYTES:
                raise ValueError("capture_exceeds_8_mib")
            artifact = {"artifact_id": new_id("artifact"), "created_at": utc_now(),
                        "source_class": "original", "origin": "selected_file_import",
                        "sha256": sha256_hex(data), "size_bytes": len(data),
                        "media_type": mimetypes.guess_type(target.name)[0] or "application/octet-stream"}
            return self._record(intent, authority, artifact=artifact, data=data)
        except (OSError, ValueError) as exc:
            return self._record(intent, authority, error=type(exc).__name__ if isinstance(exc, OSError) else str(exc))

    def _verified_asset(self, reference):
        if not self.store.verify_chain()["valid"]:
            raise ValueError("invalid_receipt_chain")
        asset = self.store.get(reference)
        if asset is None or asset.pop("kind", None) != "mirror_artifact":
            raise ValueError("unknown_mirror_artifact")
        history = [r for r in self.store.receipts() if r["output_ref"] == reference]
        if len(history) != 1:
            raise ValueError("missing_or_ambiguous_artifact_receipt")
        entry = _entry(history[0])
        _verify_asset(asset, entry)
        data = self.store.artifact_data(asset["sha256"])
        if len(data) != asset["size_bytes"]:
            raise ValueError("stored_size_mismatch")
        return asset, data, entry

    def analyze(self, reference, *, consent_scope="", actor_id="local-user"):
        intent, authority = self._authorize("artifact.derive", "artifact:" + reference, consent_scope, actor_id)
        if authority.tre_logic != "+1":
            return self._record(intent, authority)
        try:
            original, data, parent = self._verified_asset(reference)
            if original["source_class"] != "original":
                raise ValueError("analysis_requires_original")
            output = text_analysis(data)
            artifact = {"artifact_id": new_id("artifact"), "created_at": utc_now(),
                        "source_class": "derived", "adapter": ADAPTER,
                        "parent_artifact_id": reference, "parent_sha256": original["sha256"],
                        "parent_receipt_hash": parent["receipt_hash"],
                        "sha256": sha256_hex(output), "size_bytes": len(output),
                        "media_type": "application/json"}
            return self._record(intent, authority, artifact=artifact, data=output)
        except (ValueError, UnicodeError) as exc:
            return self._record(intent, authority, error="input_not_utf8" if isinstance(exc, UnicodeError) else str(exc))

    def export(self, reference, *, consent_scope="", include_original=False, actor_id="local-user"):
        intent, authority = self._authorize("artifact.export", "artifact:" + reference, consent_scope, actor_id)
        if authority.tre_logic != "+1":
            return self._record(intent, authority)
        try:
            derived, data, derived_receipt = self._verified_asset(reference)
            if derived["source_class"] != "derived":
                raise ValueError("export_requires_derived_artifact")
            original, original_data, original_receipt = self._verified_asset(derived["parent_artifact_id"])
            _verify_lineage(original, derived, original_receipt)
            if text_analysis(original_data) != data:
                raise ValueError("analysis_replay_mismatch")
            payloads = {derived["artifact_id"]: base64.b64encode(data).decode("ascii")}
            if include_original:
                payloads[original["artifact_id"]] = base64.b64encode(original_data).decode("ascii")
            manifest = {"schema_version": BUNDLE_SCHEMA, "original": original, "derived": derived,
                        "history": [original_receipt, derived_receipt], "payloads": payloads,
                        "include_original": bool(include_original)}
            result = self._record(intent, authority, metadata={
                "bundle_digest": _hash(manifest), "include_original": bool(include_original),
                "derived_ref": reference, "export_state": "prepared",
            })
            result["bundle"] = {"manifest": manifest,
                                "export_receipt": {"receipt": result["receipt"], "receipt_hash": result["receipt_hash"]}}
            return result
        except (ValueError, UnicodeError) as exc:
            return self._record(intent, authority, error=str(exc))

    def history(self, reference):
        artifact, _, receipt = self._verified_asset(reference)
        result = {"artifact": artifact, "receipt": receipt, "chain": self.store.verify_chain()}
        if artifact["source_class"] == "derived":
            parent, _, parent_receipt = self._verified_asset(artifact["parent_artifact_id"])
            _verify_lineage(parent, artifact, parent_receipt)
            result["parent"] = {"artifact": parent, "receipt": parent_receipt}
        return result


def _verify_receipt(entry):
    receipt = entry["receipt"]
    if chained_hash(receipt["previous_receipt_ref"], receipt) != entry["receipt_hash"]:
        raise ValueError("receipt_hash_mismatch")
    if receipt["authority"]["tre_logic"] != "+1" or receipt["metadata"]["verified"] is not True:
        raise ValueError("receipt_not_authorized_or_verified")
    return receipt


def _verify_asset(asset, entry):
    receipt = _verify_receipt(entry)
    source_class = asset["source_class"]
    if source_class not in {"original", "derived"}:
        raise ValueError("invalid_source_class")
    action, scope = (("artifact.capture", "local.capture") if source_class == "original"
                     else ("artifact.derive", "local.analyze"))
    if (receipt["output_ref"] != asset["artifact_id"] or receipt["source_class"] != source_class
            or receipt["metadata"]["artifact_digest"] != _hash(asset)
            or receipt["metadata"]["operation"] != action or receipt["authority"]["consent_scope"] != scope):
        raise ValueError("artifact_receipt_mismatch")


def _verify_lineage(original, derived, parent):
    if (original["source_class"] != "original" or derived["source_class"] != "derived"
            or derived["parent_artifact_id"] != original["artifact_id"]
            or derived["parent_sha256"] != original["sha256"]
            or derived["parent_receipt_hash"] != parent["receipt_hash"]
            or derived["adapter"] != ADAPTER):
        raise ValueError("lineage_mismatch")


def verify_bundle(bundle: Any, *, expected_export_hash: str | None = None) -> dict:
    """Verify a selected history and payloads without the source database.

    This checks self-consistency, not sender identity or complete global history.
    Supply an independently retained export hash to detect wholesale replacement.
    """
    try:
        manifest = bundle["manifest"]
        if manifest["schema_version"] != BUNDLE_SCHEMA:
            raise ValueError("unsupported_bundle_schema")
        export = _verify_receipt(bundle["export_receipt"])
        if expected_export_hash is not None and bundle["export_receipt"]["receipt_hash"] != expected_export_hash:
            raise ValueError("export_anchor_mismatch")
        if (export["metadata"]["bundle_digest"] != _hash(manifest)
                or export["metadata"]["operation"] != "artifact.export"
                or export["authority"]["consent_scope"] != "local.export"
                or export["metadata"]["include_original"] != manifest["include_original"]):
            raise ValueError("export_manifest_mismatch")
        original, derived = manifest["original"], manifest["derived"]
        if export["metadata"]["derived_ref"] != derived["artifact_id"]:
            raise ValueError("export_target_mismatch")
        history = manifest["history"]
        if len(history) != 2 or type(manifest["include_original"]) is not bool:
            raise ValueError("invalid_selected_history")
        _verify_asset(original, history[0])
        _verify_asset(derived, history[1])
        _verify_lineage(original, derived, history[0])
        expected = {derived["artifact_id"]}
        if manifest["include_original"]:
            expected.add(original["artifact_id"])
        if set(manifest["payloads"]) != expected:
            raise ValueError("unexpected_or_missing_payload")
        decoded = {}
        for asset in (original, derived):
            if asset["artifact_id"] not in expected:
                continue
            encoded = manifest["payloads"][asset["artifact_id"]]
            if not isinstance(encoded, str) or len(encoded) > (MAX_CAPTURE_BYTES + 2) // 3 * 4:
                raise ValueError("payload_exceeds_limit")
            data = base64.b64decode(encoded, validate=True)
            if len(data) != asset["size_bytes"] or sha256_hex(data) != asset["sha256"]:
                raise ValueError("payload_integrity_mismatch")
            decoded[asset["artifact_id"]] = data
        replay = False
        if manifest["include_original"]:
            if text_analysis(decoded[original["artifact_id"]]) != decoded[derived["artifact_id"]]:
                raise ValueError("analysis_replay_mismatch")
            replay = True
        return {"valid": True, "scope": "selected_history_and_included_payloads",
                "identity_verified": False, "original_included": manifest["include_original"],
                "analysis_replayed": replay, "anchor_checked": expected_export_hash is not None,
                "export_receipt_hash": bundle["export_receipt"]["receipt_hash"]}
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, binascii.Error, UnicodeError):
        return {"valid": False, "reason": "invalid_bundle_or_integrity_mismatch"}
