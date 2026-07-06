# MIRROR SEED MVP Backlog

**Product goal:** A mobile edge application that captures an authorized observation, preserves the original, creates a receipt, runs approved analysis, labels derivative output, and shows a human-readable history.

## Non-Goals for the First MVP

The MVP does **not** attempt to deliver:

- a replacement mobile operating system;
- autonomous financial services or token settlement;
- autonomous physical-machine control;
- a general-purpose world model;
- legal ownership enforcement;
- full XR reconstruction or production-grade digital twins.

## MVP User Flow

```text
1. User captures an image, short audio clip, note, or sensor snapshot.
2. App records device time and selected sensor context.
3. Original bytes are hashed locally.
4. A capture event and MIGIReceipt are persisted locally.
5. User selects an approved analysis action.
6. Output is stored as derived and linked to the original receipt.
7. UI shows original, derived output, authority state, and timeline.
8. Any external share or consequential action requires explicit confirmation.
```

## Milestone 0 — Foundation

- [ ] Define a versioned MUEF envelope.
- [ ] Define `MIGIReceipt` JSON schema.
- [ ] Implement a local SQLite ChainLog with a genesis hash.
- [ ] Implement `+1 / 0 / -1` Tre Logic result model with reason codes.
- [ ] Define source classes: `original`, `observed`, `derived`, `simulated`, `proposed`, `authorized`, `executed`.
- [ ] Add unit tests for canonical serialization and hash chaining.

**Acceptance:** A local CLI or API can append and verify a chain of receipts.

## Milestone 1 — Authority Core

- [ ] Define consent scope and policy request schemas.
- [ ] Implement a minimal LUFITGuard evaluator.
- [ ] Support allow, hold-for-confirmation, and deny decisions.
- [ ] Log every decision as a receipt-linked event.
- [ ] Add policy tests for sensitive data, missing consent, and external export.

**Acceptance:** An analysis request cannot run unless the policy evaluator returns an explainable `+1` or an explicit user confirmation resolves a `0` state.

## Milestone 2 — Android Capture

- [ ] Create Android project with Kotlin and Jetpack Compose.
- [ ] Capture still image metadata through CameraX.
- [ ] Capture a text note and short audio sample.
- [ ] Read permissioned sensor context where available.
- [ ] Hash original media locally.
- [ ] Use Android Keystore-backed signing when practical.
- [ ] Persist captures and receipts in encrypted local storage.

**Acceptance:** A user can capture an image and view an immutable local receipt timeline without a network connection.

## Milestone 3 — Derived Analysis

- [ ] Add one analysis adapter with an explicit privacy policy.
- [ ] Store model/provider/version metadata.
- [ ] Label generated analysis as `derived`.
- [ ] Preserve original input separately from output.
- [ ] Show provenance links from output to capture receipt.

**Acceptance:** The UI can prove which original capture produced a derived response and which policy allowed the operation.

## Milestone 4 — Audit View and Export

- [ ] Add receipt timeline and detail pages.
- [ ] Add verification screen for chain integrity.
- [ ] Export a portable receipt bundle without exposing unapproved private content.
- [ ] Add share confirmation and scope selection.
- [ ] Add basic error, recovery, and delete-request handling.

**Acceptance:** A user can inspect and export the provenance of one capture and its approved analysis.

## Milestone 5 — Optional Extensions

- [ ] Speech-to-text voice gateway.
- [ ] Sensor fusion and spatial metadata.
- [ ] Local lightweight model adapter.
- [ ] Cloud task-router adapter.
- [ ] XR or 3D preview.
- [ ] First industry adapter: vehicle condition, creator asset proof, or music-session logging.

## Technical Boundaries

```text
LLMs and vision models may recommend or classify.
LUFITGuard decides policy state.
Humans approve consequential actions.
MIGIReceipt records durable transitions.
A simulation remains a simulation until independently verified.
```

## Definition of Done

A feature is complete only when it includes:

- an explicit source classification;
- an authority path;
- a receipt or documented reason why a receipt is not applicable;
- privacy and retention notes;
- tests or manual verification steps;
- a user-visible explanation for `0` and `-1` outcomes.
