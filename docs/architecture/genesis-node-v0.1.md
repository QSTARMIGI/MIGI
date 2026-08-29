# MIGI Genesis Node v0.1

**Purpose:** prove the smallest executable MIGI loop end-to-end.

```text
Intent
  ↓
LUFITGuard + Tre Logic
  ↓
Execution
  ↓
Verification
  ↓
MIGIReceipt + SHA-256 ChainLog
  ↓
Structured Memory
  ↓
Receipt-grounded Recall
```

## Frozen v0.1 objects

- `MIGIIntent`
- `MIGIArtifact`
- `MIGIAuthority`
- `MIGIExecution`
- `MIGIReceipt`
- `MIGIMemory`

The implementation intentionally keeps these objects small. Domain-specific systems such as Alchemy, manufacturing, MIRROR SEED, QSTAR, HBC, and CAMBUS should integrate through these boundaries rather than bypassing them.

## First executable capability

Genesis v0.1 supports one operation: `artifact.inspect`.

Given a user-selected local file, the node:

1. stores the user's intent;
2. checks explicit read scope and allowed-root policy;
3. returns Tre Logic `+1`, `0`, or `-1` with a reason code;
4. on `+1`, computes SHA-256, byte size, and media type;
5. recomputes the file hash and size as execution verification;
6. creates a `migi-receipt.v0`-compatible receipt;
7. chains the receipt to the prior receipt using SHA-256;
8. stores a structured memory record; and
9. reconstructs history later from receipts plus linked execution records.

A denied or held request is also receipted, but no file content is read by the execution engine.

## Security boundary

The API allows inspection only beneath `MIGI_ALLOWED_ROOT` (default: server working directory). Merely remembering a path or command does not authorize it.

Genesis v0.1 provides **hash-chain integrity, not identity signatures**. Android Keystore-backed signing is a later MIRROR SEED milestone and must not be implied by this version.

## Deterministic hashing

The receipt chain uses deterministic JSON encoding with sorted keys and rejects floating-point values in hashed records. This is a deliberately narrow Genesis canonical format and does **not** claim full RFC 8785/JCS conformance.

## Run locally

Core CLI uses only the Python standard library:

```bash
python -m migi.cli --db .migi/genesis.db inspect ./README.md
python -m migi.cli --db .migi/genesis.db verify
python -m migi.cli --db .migi/genesis.db recall README.md
```

Optional API:

```bash
pip install -e '.[api]'
MIGI_ALLOWED_ROOT="$PWD" uvicorn migi.api:app --host 127.0.0.1 --port 8000
```

Endpoints:

```text
GET  /status
POST /execute
GET  /receipts
GET  /recall/{reference}
```

## Acceptance test

A build passes Genesis v0.1 when a real artifact can be explicitly authorized, inspected, independently verified, receipted into a valid chain, stored, and later reconstructed from durable records.

Run:

```bash
python -m unittest discover -s tests -v
```

## Next milestone

After this vertical slice is stable, the next extension is MIRROR SEED capture plus Android Keystore signatures so a phone can create signed original-observation receipts before any AI-derived transformation occurs.
