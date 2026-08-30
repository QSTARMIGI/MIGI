from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Iterable

from .authority import LUFITGuard
from .events import MUEFEvent
from .models import (
    MIGIArtifact,
    MIGIExecution,
    MIGIIntent,
    MIGIMemory,
    MIGIReceipt,
    SourceClass,
)
from .replay import replay_verified_state
from .storage import GenesisStore
from .util import new_id, utc_now


class GenesisNode:
    """MIGI Genesis Node.

    Implements an accountable vertical slice:
    intent -> authority -> execution -> verification -> receipt -> memory -> recall.

    v0.2 adds MUEF state events, deterministic replay, and a CAMbus-compatible
    event boundary without making network receipt equivalent to authorization.
    """

    VERSION = "0.2.0"

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
            "capabilities": [
                "artifact.inspect",
                "receipt.verify",
                "artifact.recall",
                "state.patch",
                "state.replay",
            ],
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
            metadata={"requested_via": "genesis.v0.2"},
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

    def process_muef_event(
        self,
        event: MUEFEvent,
        *,
        actor_id: str | None = None,
        consent_scope: str = "local.state.write",
        transport_ref: str | None = None,
    ) -> dict[str, Any]:
        """Process one MUEF state event through authority, receipt, and memory.

        v0.2 intentionally supports only `migi.state.patch`. Receiving a CAMbus
        packet does not authorize it; LUFITGuard evaluates the resulting intent.
        """
        event.validate()
        if event.event_type != "migi.state.patch":
            raise ValueError("Genesis v0.2 only executes migi.state.patch events")
        patch = event.payload.get("state_patch")
        if not isinstance(patch, dict):
            raise ValueError("migi.state.patch requires an object payload.state_patch")

        self.store.put("muef_event", event.event_id, event.occurred_at, event.to_dict())

        intent = MIGIIntent(
            intent_id=new_id("intent"),
            created_at=utc_now(),
            actor_id=actor_id or event.actor.id,
            action="state.patch",
            target_ref=f"state:{event.event_id}",
            consent_scope=consent_scope,
            metadata={
                "requested_via": "cambus" if transport_ref else "genesis.local",
                "muef_event_ref": event.event_id,
                **({"transport_ref": transport_ref} if transport_ref else {}),
            },
        )
        self.store.put("intent", intent.intent_id, intent.created_at, intent.to_dict())

        decision = self.guard.evaluate(intent)
        authority = decision.authority
        self.store.put("authority", authority.authority_id, authority.decided_at, authority.to_dict())

        if not decision.allowed:
            return self._record_event_non_execution(event, intent, authority, transport_ref)

        started_at = utc_now()
        execution = MIGIExecution(
            execution_id=new_id("exec"),
            started_at=started_at,
            completed_at=utc_now(),
            intent_id=intent.intent_id,
            authority_id=authority.authority_id,
            executor="migi.genesis.state_patch",
            operation="state.patch",
            success=True,
            output={
                "event_id": event.event_id,
                "applied_keys": sorted(str(key) for key in patch),
                "deleted_keys": sorted(str(key) for key, value in patch.items() if value is None),
            },
            verification={
                "event_valid": True,
                "state_patch_object": True,
                "authority_allowed": True,
            },
        )
        self.store.put("execution", execution.execution_id, execution.completed_at, execution.to_dict())

        receipt_metadata: dict[str, Any] = {
            "execution_ref": execution.execution_id,
            "executor": execution.executor,
            "event_type": event.event_type,
            "verified": True,
        }
        if transport_ref:
            receipt_metadata["transport_ref"] = transport_ref

        receipt = self._make_receipt(
            intent=intent,
            authority=authority,
            event_id=event.event_id,
            source_class=SourceClass.EXECUTED.value,
            output_ref=event.event_id,
            metadata=receipt_metadata,
        )
        receipt_hash = self.store.append_receipt(receipt)

        memory = MIGIMemory(
            memory_id=new_id("memory"),
            created_at=utc_now(),
            subject_ref=event.event_id,
            receipt_id=receipt.receipt_id,
            kind="migi.state.patch.completed",
            summary=f"Applied verified state patch with {len(patch)} key(s).",
            facts={
                "event_ref": event.event_id,
                "execution_ref": execution.execution_id,
                "authority_ref": authority.authority_id,
                "transport_ref": transport_ref,
            },
        )
        self.store.put("memory", memory.memory_id, memory.created_at, memory.to_dict())

        return {
            "event": event.to_dict(),
            "intent": intent.to_dict(),
            "authority": authority.to_dict(),
            "execution": execution.to_dict(),
            "receipt": receipt.to_dict(),
            "receipt_hash": receipt_hash,
            "memory": memory.to_dict(),
            "replay": self.replay_state(),
        }

    def replay_state(self) -> dict[str, Any]:
        return replay_verified_state(self.store).to_dict()

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

    def _record_event_non_execution(self, event: MUEFEvent, intent: MIGIIntent, authority, transport_ref: str | None) -> dict[str, Any]:
        metadata: dict[str, Any] = {"executed": False, "event_type": event.event_type}
        if transport_ref:
            metadata["transport_ref"] = transport_ref
        receipt = self._make_receipt(
            intent=intent,
            authority=authority,
            event_id=event.event_id,
            source_class=SourceClass.PROPOSED.value,
            output_ref=event.event_id,
            metadata=metadata,
        )
        receipt_hash = self.store.append_receipt(receipt)
        memory = MIGIMemory(
            memory_id=new_id("memory"),
            created_at=utc_now(),
            subject_ref=event.event_id,
            receipt_id=receipt.receipt_id,
            kind="migi.state.patch.not_executed",
            summary=f"State patch did not execute: {authority.reason_code}.",
            facts={
                "tre_logic": authority.tre_logic,
                "reason_code": authority.reason_code,
                "event_ref": event.event_id,
                "transport_ref": transport_ref,
            },
        )
        self.store.put("memory", memory.memory_id, memory.created_at, memory.to_dict())
        return {
            "event": event.to_dict(),
            "intent": intent.to_dict(),
            "authority": authority.to_dict(),
            "execution": None,
            "receipt": receipt.to_dict(),
            "receipt_hash": receipt_hash,
            "memory": memory.to_dict(),
            "replay": self.replay_state(),
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
