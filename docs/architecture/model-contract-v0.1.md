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


## 10. Emoji A++ and MCP boundary

**Status: proposed design decision; implementation not yet present.** Emoji A++ uses a three-state core trit. Network/context is metadata and MUST NOT be treated as a fourth trit value.

| Symbol | Trit | Proposed core meaning | Boundary rule |
|---|---:|---|---|
| 🌀 | -1 | Absorb / receive input | Receiving data does not imply permission to retain, process, or forward it. |
| ⚛️ | 0 | Observe / inspect | Observation is a typed intent, not proof that a claim is true. |
| 💠 | +1 | Emit / propose output | Emission proposes output or an action; consequential actions still require L2 authorization. |

`🌐` is a separate context flag/metadata field for network, remote-provider, or connectivity context. It is not a fourth trit and MUST NOT alter the meaning or numeric value of the three core trits. Encoding and decoding MUST preserve this separation.

### MCP adapter responsibilities

- MCP is a protocol boundary for discovering and invoking tools and accessing resources/prompts; it is not the Emoji A++ semantic model or MIGI's authorization system.
- An Emoji A++ intent MUST first be parsed into a versioned, typed intermediate representation (IR). Symbol parsing, trit validation, and schema validation happen before MCP routing.
- An MCP client adapter MAY discover candidate tools, but tool descriptions and tool results are untrusted input. Discovery does not authorize invocation.
- Before a tool call, the request MUST pass provider/tool eligibility and L2 policy checks for operation, target, arguments, data classification, consent, and risk.
- The adapter MUST validate arguments against the discovered tool schema, enforce deadlines/cancellation, and return a normalized result or typed failure. No model-generated free text may be executed as code.
- The runtime MUST record permitted provenance references for the originating intent, selected server/tool, policy decision, result digest, and receipt. Sensitive content and credentials must not enter ordinary logs.
- MCP tools, resources, and prompts MUST be represented as distinct capability types in the IR; a prompt or resource read must not be silently converted into a tool invocation.

### Initial conformance tests for Emoji A++ / MCP

1. Only 🌀, ⚛️, and 💠 map to core trit values (-1, 0, +1).
2. 🌐 is parsed as metadata and is rejected if supplied as a core trit value.
3. Encode/decode round trips preserve trit values and context metadata independently.
4. Unknown symbols, malformed sequences, and unsupported schema versions fail closed.
5. MCP tool discovery alone never authorizes a call.
6. A denied or held L2 decision results in zero MCP tool invocations.
7. Tool arguments that fail schema validation are not sent.
8. MCP timeout, cancellation, unavailable server, and malformed result become typed failures without unauthorized fallback.
9. Tool results remain distinguishable from original observations and model-generated interpretations.
10. The resulting receipt links the intent, policy decision, tool identity, and verified outcome where available.

## 11. Status and next implementation slice

**Current status: PROPOSED CONTRACT.** This document alone does not establish a model router, MCP client/server integration, local inference, external provider integration, production security, or passing conformance tests.

Recommended next implementation slice:
1. Add versioned Python dataclasses or equivalent typed models for request and proposal envelopes and Emoji A++ IR.
2. Add deterministic mock model and mock MCP tool adapters (no network calls).
3. Add schema validation and provider/tool eligibility checks.
4. Add conformance tests for trit/context separation, privacy, failure, and authority boundaries.
5. Integrate with Genesis only through existing intent/authority/receipt boundaries after reviewing their current contracts.

Keep this work on a draft branch until tests pass and a maintainer reviews compatibility with existing schemas and open PRs.

## 12. Prototype implementation status (2026-10-16)

The draft branch now contains an initial offline Python prototype:

- `migi/emoji_a_pp.py`: three-state trit mapping, versioned intent structure, canonical JSON round-trip helpers, a deliberately limited tool-input schema validator, an explicit test authority gate, a mock in-process MCP-boundary adapter, and a digest-based prototype receipt.
- `tests/test_emoji_a_pp.py`: tests for the three core trits, 🌐 metadata separation, unsupported schema versions, non-emit rejection, denied authority, invalid tool arguments, operation/tool mismatch, and receipt provenance.

**Verification status:** files have been committed to the draft branch, but the test suite has not yet been executed in a repository runtime. These tests must be run before describing the prototype as passing. The adapter is not a network MCP client and the local `AuthorityGate` is a test double, not a replacement for Genesis/LUFITGuard or production L2 authorization. The prototype receipt is a local digest record, not a signed MIGIReceipt or an append to Genesis ChainLog.
