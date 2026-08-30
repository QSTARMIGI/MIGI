# CAMbus + Deterministic Replay v0.2

> Status: experimental vertical slice

Genesis v0.2 extends the accountable core with a transport-neutral semantic packet and a replayable MUEF state transition.

## Invariant

```text
Network receipt != authorization
```

A CAMbus packet may deliver a MUEF event to a node. The receiving node must still create an intent and pass LUFITGuard/Tre Logic before the event can become an executed state transition.

## Executable path

```text
Node A
  |
  | SymbolPacket / CAMbus v0
  v
Node B
  |
  v
MUEF validation
  |
  v
MIGIIntent(state.patch)
  |
  v
LUFITGuard
  |             \
 +1              0 / -1
  |                \
  v                 v
execution        no execution
  |                 |
  +--------+--------+
           v
      MIGIReceipt
           |
           v
      receipt chain
           |
           v
 deterministic replay
```

## MUEF state patch

v0.2 executes one deliberately narrow event type:

```json
{
  "schema_version": "muef.v0",
  "event_type": "migi.state.patch",
  "payload": {
    "state_patch": {
      "mode": "active"
    }
  }
}
```

A JSON `null` value deletes a state key during replay. All other values replace the key. Replay applies patch keys in sorted order and only applies events that have an `executed` receipt with Tre Logic `+1`.

## Authority

`state.patch` requires:

```text
consent_scope = local.state.write
or
consent_scope = private.local.state.write
```

and the internal intent target must be a `state:` reference.

CAMbus does not bypass this policy.

## CAMbus v0

The initial wire representation is canonical JSON with a 4-byte network-order length prefix.

`SymbolPacket` carries:

- protocol version
- packet ID
- correlation ID
- source node
- destination node
- QoS profile
- one MUEF event

The first adapter uses TCP only to prove the transport boundary. CAN, WebSocket, optical/LiFi, or other adapters can implement the same packet contract later.

## Replay output

Replay returns:

- materialized state
- count of applied events
- count of preserved but skipped events
- verified receipt-chain head
- deterministic SHA-256 state hash

This lets two implementations compare a replay result by state hash without treating the materialized state store as the source of truth.

## Acceptance criteria

1. MUEF event validation passes.
2. CAMbus round-trip preserves event identity.
3. `state.patch` requires explicit local state-write authority.
4. Held/denied events remain stored but do not alter replay state.
5. Executed events produce receipts linked into the existing Genesis receipt chain.
6. Replay refuses to operate when the receipt chain is invalid.
7. A two-node localhost test sends a MUEF event over CAMbus and reconstructs the resulting state on Node B.
