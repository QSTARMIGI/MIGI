# MIGI Model Contract v0.1

> **Status:** Draft architecture contract; not yet an implemented runtime feature.
> **Target:** Hybrid external and local model providers governed by MIGI Core.
> **Compatibility:** Additive proposal. Does not replace Genesis Node, MIGIReceipt, MUEF, LUFITGuard, Tre Logic, or existing project contracts.

## 1. Purpose

Define a provider-neutral boundary between MIGI intelligence (L4), authority (L2), and execution (L3). External and local models may propose structured outputs, but no model response grants itself permission to execute an action.

## 2. Five-layer placement

- **L1 — Substrate:** OS, files, storage, networking, cryptographic primitives, and available hardware.
- **L2 — Authority:** Validates identity/context, consent scope, policy, risk limits, and action authorization. A model must not override this layer.
- **L3 — Execution / STARGATE:** Executes only typed operations approved by L2; applies timeouts, bounded resources, and result verification.
- **L4 — Intelligence:** Model selection, prompt construction, inference, retrieval, planning, and structured proposal validation.
- **L5 — Presentation:** User-facing text, voice, camera, web, mobile, and XR interfaces.

Layer labels are architectural responsibilities, not claims that every adapter or surface currently exists.

## 3. Required request envelope

Every inference request SHOULD carry:
- `contract_version` (initial value: `migi.model.v0`)
- `request_id` (unique opaque identifier)
- `intent_ref` (reference to the originating MIGI intent)
- `task_type` (registered task identifier)
- `input_refs` (references to authorized inputs; avoid copying sensitive content into logs)
- `data_classification` and `allowed_provider_classes`
- `output_schema_ref`
- `resource_limits` (deadline, token/output limit, and cost limit where applicable)
- `policy_context_ref` (reference, not a model-authored policy)
- `trace_context` (optional correlation identifiers)

The gateway MUST reject missing required fields, unknown contract versions, invalid references, and requests whose data classification conflicts with allowed provider classes.

## 4. Model proposal envelope

A provider adapter returns a proposal, never an authorization:
- `request_id`
- `provider_id` and `model_id`
- `provider_version` or deployment identifier when available
- `output_schema_ref`
- `structured_output`
- `input_refs` and evidence references used, when available
- `finish_reason` and `usage` when supported
- `warnings` and `errors`
- `started_at`, `completed_at`, and measured latency

The adapter MUST treat model output as untrusted data. Parse against a registered schema; reject malformed output; do not execute code or tool calls embedded in free text. Provider-reported confidence is metadata, not proof of correctness.

## 5. Provider eligibility and routing

The router MAY select a local or external provider only after checking:
1. task capability and modality;
2. input classification and explicit provider allowlist;
3. user policy and consent;
4. model availability and minimum resource requirements;
5. latency and cost budgets;
6. fallback rules that do not silently weaken privacy or authorization.

If no eligible provider is available, fail closed for sensitive or consequential tasks. A cloud fallback that sends previously local-only data requires an explicit policy allowance and, where required, renewed user consent.

## 6. Authority and execution invariants

- Model output MUST NOT directly invoke L3 tools.
- Every consequential operation MUST be represented as a typed action proposal.
- L2 MUST independently validate action type, target, arguments, actor, consent scope, and risk policy.
- A deny or hold decision MUST prevent execution.
- Authorization to analyze an input does not imply authorization to transmit it to another provider or to modify external state.
- Tool output and model-generated summaries MUST remain distinguishable from original observations.
- After execution, L3 MUST report the actual outcome; the runtime SHOULD independently verify state changes where feasible.
- Receipt creation records what the runtime observed and checked; it does not prove an unobserved real-world claim.

## 7. Provenance and receipt linkage

For each completed inference task, the runtime SHOULD preserve references to:
- originating intent and authorized input artifacts;
- selected provider/model and relevant version;
- output schema version and validated output digest;
- applicable authority decision and reason code;
- execution/result verification, if any;
- resulting MIGIReceipt/ChainLog references.

Do not store API secrets, credentials, raw private prompts, or sensitive input content in ordinary logs. Store only what policy permits, and define retention/deletion behavior. Hashes support integrity checks but do not establish source truth. Device identity signatures remain a separate cryptographic capability.

## 8. Failure behavior

Adapters must normalize at least: timeout, cancellation, provider unavailable, rate limit, authentication failure, invalid output, schema mismatch, policy denial, budget exceeded, and transport failure. Retry only bounded, idempotent inference requests; never automatically repeat a consequential external action without its own idempotency and authorization controls.

A provider failure MUST NOT silently cause a less-private provider to receive data. Fallback behavior must be deterministic, policy-constrained, and recorded.

## 9. Minimum conformance tests

A future implementation is not conformant until tests demonstrate:
1. Local and external mock adapters satisfy the same contract.
2. Unknown contract versions and malformed proposals are rejected.
3. Provider allowlists prevent disallowed transmission.
4. A provider timeout returns a bounded failure and does not execute an action.
5. A model proposal cannot bypass L2 to invoke L3.
6. Deny and hold decisions result in zero consequential execution.
7. Provider fallback cannot widen data permissions silently.
8. Output and receipt links preserve request, model, and authority provenance.
9. Altered receipt records are detected by the existing chain verifier.
10. Secrets and prohibited input content do not leak into logs or receipts.

## 10. Status and next implementation slice

**Current status: PROPOSED CONTRACT.** This document alone does not establish a model router, local inference, external provider integration, provider authentication, production security, or passing conformance tests.

Recommended next implementation slice:
1. Add versioned Python dataclasses or equivalent typed models for request and proposal envelopes.
2. Add a provider protocol and deterministic mock-local/mock-external adapters (no network calls).
3. Add schema validation and routing eligibility checks.
4. Add conformance tests for privacy, failure, and authority boundaries.
5. Integrate with Genesis only through existing intent/authority/receipt boundaries after reviewing their current contracts.

Keep this work on a draft branch until tests pass and a maintainer reviews compatibility with existing schemas and open PRs.
