# MIRROR SEED MS-001 — offline capture-to-export core

Status: implemented for local Python/CLI use; native phone acceptance is pending.

## Outcome

A user-selected file is preserved as original bytes, explicitly authorized for
one deterministic analysis, linked to a derived artifact, and exported in a
portable JSON bundle. A separate process can verify the bundle without the
source file or database. When original bytes are included, the verifier reruns
the analysis and compares its output.

MS-001 uses the existing Genesis objects, LUFITGuard, SQLite store, canonical
hashing, and receipt chain. It requires Python 3.11+ and no extra dependencies.

## Run the complete public-sample demo

From the repository root:

```bash
PYTHONPATH=. python examples/mirror_seed_demo.py --output .migi/mirror-demo.json
python -m migi.cli mirror-verify .migi/mirror-demo.json
```

The demo deletes its input and temporary database before verifying. It prints
an export receipt hash; retain that hash separately. For an anchored check:

```bash
python -m migi.cli mirror-verify .migi/mirror-demo.json --expected-export-hash HASH_FROM_DEMO
```

The output file must not already exist. The sample is generated text, not a
camera observation. No data is uploaded.

## Use a selected file

```bash
python -m migi.cli --db .migi/genesis.db mirror-capture note.txt --scope local.capture
python -m migi.cli --db .migi/genesis.db mirror-analyze ORIGINAL_ARTIFACT_ID --scope local.analyze
python -m migi.cli --db .migi/genesis.db mirror-history DERIVED_ARTIFACT_ID
python -m migi.cli --db .migi/genesis.db mirror-export DERIVED_ARTIFACT_ID bundle.json --scope local.export
python -m migi.cli mirror-verify bundle.json
```

Copy the returned artifact IDs into subsequent commands. A missing or wrong
scope produces Tre `0` and a non-execution receipt. Capture paths outside the
configured allowed roots produce `-1`. CLI capture treats the explicitly
selected file's parent as its allowed root. Library callers supply their own
trusted roots.

Capture accepts at most 8 MiB. `migi.text-stats.v1` analyzes strictly decoded
UTF-8 text and records byte, character, whitespace-separated word, and line
counts. The derived JSON records its adapter version and input hash. It is a
deterministic demonstration adapter, with no model or cloud provider involved.
Binary originals can be preserved, but this adapter refuses to analyze them.

## Storage and integrity

- Original and derived bytes are stored by SHA-256 in SQLite `artifact_bytes`.
- Intent, authority, execution, memory, artifact descriptor, bytes, and receipt
  commit in one transaction for each new MIRROR operation.
- Failed transactions leave no partial operation or new orphan bytes.
- Every artifact descriptor is bound into its receipt by a canonical digest.
- The derived descriptor binds the original artifact ID, original byte hash,
  and original capture receipt hash.
- Receipts use the existing Genesis chain. New transactions select their head
  under SQLite's write lock. Legacy appenders reject a stale head under the
  same lock, avoiding a race that could fork the chain.
- Missing, changed, or unreceipted data cannot become a successful derivative
  or successful export.
- A held request and an analysis failure are recorded with distinct authority
  and execution states.

## Export contract and privacy

The top-level bundle contains `manifest` and `export_receipt`. The manifest
contains the original and derived descriptors, their two selected receipts,
base64-encoded included payloads, and an `include_original` boolean. The export
receipt binds the whole manifest digest, selection, and local export consent.
Its `export_state: prepared` means the bundle was prepared, not delivered to
any recipient. A subsequent output-write failure does not claim delivery.

Default export includes derived bytes and the original's hash/size descriptor,
but excludes original bytes. Add `--include-original` to include the original
and enable independent analysis replay. Hashes, lengths, timestamps, and
analysis statistics still reveal metadata: inspect the bundle before sharing.
Original local paths, source filenames, actor records, unrelated receipts,
and unrelated assets are not included.

The standalone verifier checks selected receipt hashes, descriptor bindings,
authority scopes, parent lineage, payload hashes/sizes, and the export manifest
commitment. Its scope is selected history and included payloads. A redacted
bundle cannot verify omitted original bytes or reproduce the analysis. The
full global receipt chain is checked locally, not exported with private history.

## Trust boundary

This is a trusted local-user prototype. Scope strings express that local user's
explicit choice; they are not authentication credentials. Actor IDs are
self-declared. There is no multi-user API for these commands.

Receipts are unsigned. An attacker able to replace a whole bundle can recompute
its hashes; an independently retained export hash detects replacement relative
to that anchor. This is not device identity, trusted timestamping, authorship,
legal ownership, or proof that an observation describes physical reality.

The original is exactly the byte sequence imported. Cooperative local files
are assumed; adversarial concurrent directory replacement or source writes
are outside this milestone. The database is not encrypted by this change.
Retention/deletion controls and authenticated encrypted device storage remain
phone-release requirements.

## Acceptance evidence

The test suite covers source deletion and restart, separate consent scopes,
root/symlink rejection, redacted export, payload/receipt/descriptor tampering,
independent anchoring, malformed bundles, binary/oversize input, atomic rollback,
concurrent captures, and a separate-process CLI round trip. The CLI verifier
opens no database.

## Next milestone: MS-002 phone acceptance

1. Capture a note or image through the native phone UI.
2. Preserve the original in protected local storage.
3. Show original/derived labels and reasoned `+1 / 0 / -1` decisions.
4. Connect one compatible analysis adapter to the same provenance contract.
5. Add device-backed signing and independent public-key verification.
6. Verify a capture, derived result, history, and consent-selected export while
   offline on the target phone; record install/build and performance evidence.

MS-001 does not complete camera capture, Android Keystore signing, a UI, sensor
fusion, XR rendering, payments, or the customer pilot.
