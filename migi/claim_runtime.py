from __future__ import annotations

from typing import Any, Iterable

from .authority import LUFITGuard
from .epistemics import (
    ClaimRequirements,
    EvidenceItem,
    LUFITProfile,
    SFOObservation,
    SFORecord,
    evaluate_evidence,
    qualify_factual_claim,
    validate_profile,
)
from .models import MIGIExecution, MIGIIntent, MIGIMemory, MIGIReceipt, SourceClass, TreLogic
from .storage import GenesisStore
from .util import new_id, utc_now


class VerifiableClaimRuntime:
    """MIGI-CS-002 vertical slice for evidence-bounded claim qualification.

    This runtime composes with the existing GenesisStore and LUFITGuard. It does
    not perform physical/world-changing actions. It records a reasoning intent,
    evaluates evidence and the LUFIT profile, preserves SFO state/observation
    boundaries, issues a derived receipt, and writes a recallable memory.
    """

    VERSION = "0.1.0"

    def __init__(self, store: GenesisStore, guard: LUFITGuard):
        self.store = store
        self.guard = guard

    def qualify_claim(
        self,
        claim_ref: str,
        *,
        state_before: Any,
        state_after: Any,
        observation: SFOObservation,
        evidence: Iterable[EvidenceItem],
        profile: LUFITProfile,
        requirements: ClaimRequirements,
        actor_id: str = "local-user",
        consent_scope: str = "local.reason",
        threshold: float = 0.60,
    ) -> dict[str, Any]:
        if not claim_ref.strip():
            raise ValueError("claim_ref is required")
        observation.validate()

        intent = MIGIIntent(
            intent_id=new_id("intent"),
            created_at=utc_now(),
            actor_id=actor_id,
            action="claim.qualify",
            target_ref=f"claim:{claim_ref}",
            consent_scope=consent_scope,
            metadata={"requested_via": "migi-cs-002", "claim_ref": claim_ref},
        )
        self.store.put("intent", intent.intent_id, intent.created_at, intent.to_dict())

        decision = self.guard.evaluate(intent)
        authority = decision.authority
        self.store.put("authority", authority.authority_id, authority.decided_at, authority.to_dict())
        if not decision.allowed:
            return self._record_non_execution(claim_ref, intent, authority)

        assessment = evaluate_evidence(evidence, threshold=threshold)
        profile_status = validate_profile(profile, requirements)
        qualification = qualify_factual_claim(
            source_class=observation.source_class,
            profile_status=profile_status,
            assessment=assessment,
        )
        sfo = SFORecord(
            state_before=state_before,
            state_after=state_after,
            observation=observation,
        )

        started_at = utc_now()
        output = {
            "claim_ref": claim_ref,
            "qualification": qualification,
            "assessment": assessment.to_dict(),
            "profile": profile_status.to_dict(),
            "sfo": sfo.to_dict(),
        }
        execution = MIGIExecution(
            execution_id=new_id("exec"),
            started_at=started_at,
            completed_at=utc_now(),
            intent_id=intent.intent_id,
            authority_id=authority.authority_id,
            executor="migi.claim_runtime.qualify_claim",
            operation="claim.qualify",
            success=True,
            output=output,
            verification={
                "authority_allowed": True,
                "evidence_evaluated": True,
                "profile_checked": True,
                "simulation_preserved": (
                    observation.source_class != SourceClass.SIMULATED.value
                    or qualification == "simulation_only"
                ),
            },
        )
        self.store.put("execution", execution.execution_id, execution.completed_at, execution.to_dict())

        receipt = self._make_receipt(
            intent=intent,
            authority=authority,
            event_id=execution.execution_id,
            source_class=SourceClass.DERIVED.value,
            output_ref=f"claim:{claim_ref}",
            metadata={
                "execution_ref": execution.execution_id,
                "qualification": qualification,
                "observation_source_class": observation.source_class,
                "profile_status": profile_status.to_dict()["status"],
                "verified": True,
            },
        )
        receipt_hash = self.store.append_receipt(receipt)

        memory = MIGIMemory(
            memory_id=new_id("memory"),
            created_at=utc_now(),
            subject_ref=f"claim:{claim_ref}",
            receipt_id=receipt.receipt_id,
            kind="migi.claim.qualified",
            summary=(
                f"Claim {claim_ref} qualified as {qualification}; "
                f"Tre evidence state {assessment.state}; "
                f"LUFIT {profile_status.to_dict()['status']}."
            ),
            facts={
                "claim_ref": claim_ref,
                "qualification": qualification,
                "tre_evidence_state": assessment.state,
                "support_score": assessment.support_score,
                "confidence": assessment.confidence,
                "uncertainty": assessment.uncertainty,
                "profile_status": profile_status.to_dict()["status"],
                "execution_ref": execution.execution_id,
                "authority_ref": authority.authority_id,
            },
        )
        self.store.put("memory", memory.memory_id, memory.created_at, memory.to_dict())

        return {
            "intent": intent.to_dict(),
            "authority": authority.to_dict(),
            "execution": execution.to_dict(),
            "receipt": receipt.to_dict(),
            "receipt_hash": receipt_hash,
            "memory": memory.to_dict(),
            "chain": self.store.verify_chain(),
        }

    def recall_claim(self, claim_ref: str) -> dict[str, Any] | None:
        subject_ref = f"claim:{claim_ref}"
        memories = [m for m in self.store.list_kind("memory") if m.get("subject_ref") == subject_ref]
        receipts = [r for r in self.store.receipts() if r.get("output_ref") == subject_ref]
        if not memories and not receipts:
            return None

        history: list[dict[str, Any]] = []
        for receipt in receipts:
            intent = self.store.get(receipt["intent_ref"])
            execution_ref = receipt.get("metadata", {}).get("execution_ref")
            execution = self.store.get(execution_ref) if execution_ref else None
            history.append({"receipt": receipt, "intent": intent, "execution": execution})

        return {
            "claim_ref": claim_ref,
            "history": history,
            "memories": memories,
            "chain": self.store.verify_chain(),
        }

    def _record_non_execution(self, claim_ref: str, intent: MIGIIntent, authority) -> dict[str, Any]:
        receipt = self._make_receipt(
            intent=intent,
            authority=authority,
            event_id=authority.authority_id,
            source_class=SourceClass.PROPOSED.value,
            output_ref=f"claim:{claim_ref}",
            metadata={"executed": False, "qualification": "not_evaluated"},
        )
        receipt_hash = self.store.append_receipt(receipt)
        memory = MIGIMemory(
            memory_id=new_id("memory"),
            created_at=utc_now(),
            subject_ref=f"claim:{claim_ref}",
            receipt_id=receipt.receipt_id,
            kind="migi.claim.not_executed",
            summary=f"Claim qualification did not execute: {authority.reason_code}.",
            facts={"tre_logic": authority.tre_logic, "reason_code": authority.reason_code},
        )
        self.store.put("memory", memory.memory_id, memory.created_at, memory.to_dict())
        return {
            "intent": intent.to_dict(),
            "authority": authority.to_dict(),
            "execution": None,
            "receipt": receipt.to_dict(),
            "receipt_hash": receipt_hash,
            "memory": memory.to_dict(),
            "chain": self.store.verify_chain(),
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
        if source_class == SourceClass.EXECUTED.value and authority.tre_logic != TreLogic.ALLOW.value:
            raise ValueError("executed receipt requires Tre Logic +1 authority")
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
