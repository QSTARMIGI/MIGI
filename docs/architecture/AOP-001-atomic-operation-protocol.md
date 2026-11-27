# AOP-001 — MIGI Atomic Operation Protocol

**Status:** Proposed implementation, dependent on MIRROR SEED MS-001  
**Branch:** feat/aop-001-atomic-operation-protocol  
**Parent:** PR #15, feat/mirror-seed-capture-export  
**Scope:** Local SQLite single-database operation commits

## 1. Normative invariant

An operation is committed only when its complete evidence set and its receipt-chain entry are committed in one SQLite transaction. If any write fails before commit, none of that operation's database writes may remain visible.

The protocol does not make content true, authenticate its author, establish trusted time, or prove a physical-world observation. It establishes local transactional completeness and tamper-evident ordering under the stated storage trust assumptions.

## 2. Operation lifecycle

Intent -> Authority decision -> Execute / verify outside the write transaction -> Stage complete evidence envelope in memory -> Validate envelope -> BEGIN IMMEDIATE -> Read current receipt-chain head -> Bind receipt to that head -> Insert blobs -> Insert evidence objects -> Insert receipt and chain hash -> COMMIT -> Return committed receipt.

A failed validation or execution may produce a denial/failure receipt, but that record must also be staged and committed atomically. No success receipt may be returned before the database commit succeeds.

## 3. Contract implemented in this branch

migi.operations provides:
- OperationObject: typed storage object with kind, ID, timestamp, and payload.
- AtomicOperation: immutable staged envelope containing a receipt, evidence objects, blobs, and operation ID.
- stage_operation(...): materializes iterables before transaction entry.
- AtomicOperation.commit(store): adds the operation ID to receipt metadata and delegates one atomic commit to the store.

MIRROR SEED now routes its evidence writes through this protocol facade. The storage implementation remains the transaction owner.

## 4. Storage transaction rules

1. Open a dedicated SQLite connection for the operation.
2. Use a finite, explicit lock wait (busy_timeout_seconds, default 30 seconds).
3. Start BEGIN IMMEDIATE before reading the current receipt head.
4. Compute the receipt link from the head observed inside that transaction.
5. Write all blobs, objects, and the receipt using that connection.
6. Commit once, after every write succeeds.
7. On any exception, explicitly roll back if a transaction remains active, then re-raise.
8. A lock timeout fails the complete operation. Do not retry only the receipt append. A caller retry must restage/revalidate and retry the entire operation.

SQLite permits only one active writer per database file. BEGIN IMMEDIATE reserves the write transaction before the chain-head read; it can itself return SQLITE_BUSY when another writer holds the write transaction. This protocol therefore uses bounded waiting and fail-closed behavior, not a promise that contention can never fail.

## 5. Multi-process test

The test suite adds independent spawned processes, each constructing its own MirrorSeed/SQLite connection and attempting to append to the same database. Acceptance requires:
- every submitted capture succeeds within the configured wait;
- the chain verifies;
- exactly one receipt per operation exists;
- no duplicate receipt hashes or forked links exist.

Thread-level testing remains in place. CI must execute both tests on the branch head.

## 6. Explicit boundaries and unresolved work

### Not yet migrated
The existing Genesis v0.2 inspect_artifact and process_muef_event flows still persist some objects before calling legacy append_receipt. AOP-001's current adapter is used by MIRROR SEED only. Genesis must be migrated in a follow-up change using the same staged envelope, including a deliberate retry/rebuild policy. Until then, the legacy stale-head/orphan-object issue remains open.

### Not a distributed transaction protocol
This design is for one SQLite database file on one host. SQLite WAL is not suitable for a database file shared over a network filesystem. Multi-device synchronization, remote execution, and multi-node consensus require a separate protocol.

### Not idempotent across caller retries yet
The operation ID is recorded in receipt metadata for correlation, but this first version does not enforce uniqueness or return a previous result for a repeated operation ID. Do not assume retry deduplication. A later schema migration may add a unique operation registry and explicit idempotency semantics.

### No cryptographic signer
Receipts remain unsigned hash-chain records. Device identity, key custody, trusted timestamps, and external anchoring are outside AOP-001.

### No delivery guarantee
An export receipt marked prepared does not prove a bundle was written, transferred, or received. Delivery requires a separate event and evidence.

## 7. Acceptance gates

- [ ] Parent PR #15 is reviewed and merged, or this branch is explicitly rebased after parent changes.
- [ ] Existing MIRROR SEED test suite passes.
- [ ] New multi-process writer test passes repeatedly in CI.
- [ ] Atomic rollback tests pass for object/blob/receipt write failures.
- [ ] The full quality gate passes on the exact AOP branch head.
- [ ] Review confirms no changes to main and no premature merge.
- [ ] Genesis v0.2 migration is separately tracked and completed before claiming platform-wide AOP coverage.

## 8. Decision

This branch is a first implementation of the shared operation envelope and SQLite transaction contract. It is not yet the universal MIGI transaction layer. Keep it dependent on PR #15 until that parent is accepted, and do not merge either change solely because the static design looks correct.
