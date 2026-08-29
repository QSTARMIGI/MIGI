from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Iterable

from .authority import LUFITGuard
from .models import (
    MIGIArtifact,
    MIGIExecution,
    MIGIIntent,
    MIGIMemory,
    MIGIReceipt,
    SourceClass,
)
from .storage import GenesisStore
from .util import new_id, utc_now


class GenesisNode:
    """MIGI Genesis Node v0.1.

    Implements one accountable vertical slice:
    intent -> authority -> execution -> verification -> receipt -> memory -> recall.
    """

    VERSION = "0.1.0"

    def __init__(self, db_path: str | Path, allowed_roots: Iterable[str | Path] | None = None):
        roots = list(allowed_roots or [Path.cwd()])
        self.store = GenesisStore(db_path)
        self.guard = LUFITGuard(Path(root) for root in roots)

    def status(self) -> dict[str, Any]:
        verification = self.store.verify_chain()
        return {
            "service": "migi-genesis-node",
            "version": self.VERSION,
            "receipt_chain": verification,
            "capabilities": ["artifact.inspect", "receipt.verify", "artifact.recall"],
        }

    def inspect_artifact(
        self,
        path: str | Path,
        *,
        actor_id: str = "local-user",
        consent_scope: str = "local.read",
    ) -> dict[str, Any]:
        target = Path(path).expanduser().resolve()
        intent = MIGIIntent(
            intent_id=new_id("intent"),
            created_at=utc_now(),
            actor_id=actor_id,
            action="artifact.inspect",
            target_ref=str(target),
            consent_scope=consent_scope,
            metadata={"requested_via": "genesis.v0.1"},
        )
        self.store.put("intent", intent.intent_id, intent.created_at, intent.to_dict())

        decision = self.guard.evaluate(intent)
        authority = decision.authority
        self.store.put("authority", authority.authority_id, authority.decided_at, authority.to_dict())

        if not decision.allowed:
            return self._record_non_execution(intent, authority)

        started_at = utc_now()
        digest, size_bytes = _hash_file(target)
        media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        artifact = MIGIArtifact(
            artifact_id=new_id("artifact"),
            observed_at=utc_now(),
            path=str(target),
            sha256=digest,
            size_bytes=size_bytes,
            media_type=media_type,
        )
        self.store.put("artifact", artifact.artifact_id, artifact.observed_at, artifact.to_dict())

        verify_digest, verify_size = _hash_file(target)
        verification = {
            "sha256_match": verify_digest == digest,
            "size_match": verify_size == size_bytes,
        }
        success = all(verification.values())
        execution = MIGIExecution(
            execution_id=new_id("exec"),
            started_at=started_at,
            completed_at=utc_now(),
            intent_id=intent.intent_id,
            authority_id=authority.authority_id,
            executor="migi.genesis.artifact_inspector",
            operation="artifact.inspect",
            success=success,
            output={
                "artifact_id": artifact.artifact_id,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
                "media_type": artifact.media_type,
            },
            verification=verification,
        )
        self.store.put("execution", execution.execution_id, execution.completed_at, execution.to_dict())

        receipt = self._make_receipt(
            intent=intent,
            authority=authority,
            event_id=execution.execution_id,
            source_class=SourceClass.EXECUTED.value,
            output_ref=artifact.artifact_id,
            metadata={
                "execution_ref": execution.execution_id,
                "executor": execution.executor,
                "verified": success,
            },
        )
        receipt_hash = self.store.append_receipt(receipt)

        memory = MIGIMemory(
            memory_id=new_id("memory"),
            created_at=utc_now(),
            subject_ref=artifact.artifact_id,
            receipt_id=receipt.receipt_id,
            kind="artifact.inspect.completed",
            summary=(
                f"Inspected {target.name}; SHA-256 {artifact.sha256}; "
                f"{artifact.size_bytes} bytes; media type {artifact.media_type}."
            ),
            facts={
                "artifact_sha256": artifact.sha256,
                "execution_ref": execution.execution_id,
                "authority_ref": authority.authority_id,
                "verified": success,
            },
        )
        self.store.put("memory", memory.memory_id, memory.created_at, memory.to_dict())

        return {
            "intent": intent.to_dict(),
            "authority": authority.to_dict(),
            "execution": execution.to_dict(),
            "artifact": artifact.to_dict(),
            "receipt": receipt.to_dict(),
            "receipt_hash": receipt_hash,
            "memory": memory.to_dict(),
        }

    def recall_artifact(self, reference: str) -> dict[str, Any] | None:
        artifact = self._find_artifact(reference)
        if artifact is None:
            return None

        receipts = [r for r in self.store.receipts() if r.get("output_ref") == artifact["artifact_id"]]
        memories = [m for m in self.store.list_kind("memory") if m.get("subject_ref") == artifact["artifact_id"]]

        reconstructed: list[dict[str, Any]] = []
        for receipt in receipts:
            intent = self.store.get(receipt["intent_ref"])
            execution_ref = receipt.get("metadata", {}).get("execution_ref")
            execution = self.store.get(execution_ref) if execution_ref else None
            reconstructed.append(
                {
                    "receipt": receipt,
                    "intent": intent,
                    "execution": execution,
                }
            )

        return {
            "artifact": artifact,
            "history": reconstructed,
            "memories": memories,
            "chain": self.store.verify_chain(),
        }

    def _find_artifact(self, reference: str) -> dict[str, Any] | None:
        for artifact in self.store.list_kind("artifact"):
            if reference in {
                artifact.get("artifact_id"),
                artifact.get("sha256"),
                artifact.get("path"),
                Path(str(artifact.get("path", ""))).name,
            }:
                return artifact
        return None

    def _record_non_execution(self, intent: MIGIIntent, authority) -> dict[str, Any]:
        receipt = self._make_receipt(
            intent=intent,
            authority=authority,
            event_id=authority.authority_id,
            source_class=SourceClass.PROPOSED.value,
            output_ref=authority.authority_id,
            metadata={"executed": False},
        )
        receipt_hash = self.store.append_receipt(receipt)
        memory = MIGIMemory(
            memory_id=new_id("memory"),
            created_at=utc_now(),
            subject_ref=intent.intent_id,
            receipt_id=receipt.receipt_id,
            kind="artifact.inspect.not_executed",
            summary=f"Artifact inspection did not execute: {authority.reason_code}.",
            facts={"tre_logic": authority.tre_logic, "reason_code": authority.reason_code},
        )
        self.store.put("memory", memory.memory_id, memory.created_at, memory.to_dict())
        return {
            "intent": intent.to_dict(),
            "authority": authority.to_dict(),
            "execution": None,
            "artifact": None,
            "receipt": receipt.to_dict(),
            "receipt_hash": receipt_hash,
            "memory": memory.to_dict(),
        }

    def _make_receipt(
        self,
        *,
        intent: MIGIIntent,
        authority,
        event_id: str,
        source_class: str,
        output_ref: str,
        metadata: dict[str, Any],
    ) -> MIGIReceipt:
        return MIGIReceipt(
            schema_version="migi-receipt.v0",
            receipt_id=new_id("receipt"),
            issued_at=utc_now(),
            event_id=event_id,
            source_class=source_class,
            intent_ref=intent.intent_id,
            output_ref=output_ref,
            previous_receipt_ref=self.store.latest_receipt_hash(),
            authority={
                "tre_logic": authority.tre_logic,
                "reason_code": authority.reason_code,
                "consent_scope": authority.consent_scope,
            },
            metadata=metadata,
        )


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size
