# 💠 MIGI

**Machine International Global Intelligence** is an architecture for turning authorized observations and user work into traceable, explainable, permission-controlled outcomes.

> **Original is truth. Enhancement is derivative. Simulation is not reality. Action requires permission.**

## Current Focus

MIGI is in an architecture-and-MVP implementation phase. The executable core now starts with **Genesis Node v0.1**, which proves intent → authority → execution → verification → receipt → memory → recall. The first practical product path remains **MIRROR SEED**: trusted mobile capture, local provenance, explainable analysis, human approval, and a replayable receipt trail.

MIGI is designed as a modular system rather than a single model or platform:

```text
Signal
  ↓
Observation
  ↓
Structured Meaning
  ↓
Authority + Provenance
  ↓
Intelligence + Simulation
  ↓
Human Decision
  ↓
Digital or Physical Action
  ↓
Receipt + Audit Trail
```

## Core Building Blocks

| Project | Responsibility |
|---|---|
| **MIGI Kernel** | Coordinates intents, policy checks, task routing, and state updates. |
| **MUEF** | MIGI Unified Event Framework; a shared event envelope across services and industry adapters. |
| **MIGIReceipt** | Signed provenance object for captures, transformations, decisions, and actions. |
| **ChainLog** | Append-only lineage trail linking receipts and state transitions. |
| **LUFITGuard** | Consent, scope, risk, budget, and tool-permission policy gate. |
| **Tre Logic** | Explainable `+1 / 0 / -1` authorization state: proceed, hold, or deny. |
| **Task Router** | Chooses an approved local, cloud, tool, device, or human execution path. |
| **MIRROR SEED** | Mobile edge MVP for capture → explain → prove. |
| **Project Strawberry / Q★** | Future simulation and spatial-intelligence layer. |
| **Alchemy IDE / Emoji A++** | Future workflow authoring and symbolic orchestration layer. |

## Architecture Documentation

- [Internal Operating Projects](docs/architecture/internal-operating-projects.md)
- [Genesis Node v0.1](docs/architecture/genesis-node-v0.1.md)
- [Repository Roles and Source Provenance](docs/architecture/repository-roles.md)
- [MIRROR SEED MVP Backlog](docs/roadmap/mirror-seed-mvp.md)

## MVP Scope

The first executable MIGI foundation prioritizes:

```text
1. Identity and local device keys
2. MUEF event format
3. ChainLog and MIGIReceipt
4. LUFITGuard + Tre Logic
5. Kernel task execution
6. Local storage and basic audit view
7. Mobile capture pipeline
8. Task routing and first adapter
```

The initial user flow is intentionally small:

```text
Capture an image, audio clip, note, or sensor snapshot
  ↓
Hash and classify the original locally
  ↓
Create a MIGIReceipt
  ↓
Run approved analysis
  ↓
Label output as derived or simulated
  ↓
Show history and request human approval before consequential action
```

## Genesis Node v0.1

The first executable vertical slice lives in `migi/` and uses SQLite for durable local state. Core CLI operation requires only the Python standard library.

```bash
python -m migi.cli --db .migi/genesis.db inspect ./README.md
python -m migi.cli --db .migi/genesis.db verify
python -m migi.cli --db .migi/genesis.db recall README.md
```

The optional FastAPI surface matches the planned kernel boundary:

```text
GET  /status
POST /execute
GET  /receipts
GET  /recall/{reference}
```

Run the acceptance suite with:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

Genesis v0.1 provides SHA-256 hash-chain integrity. Device identity signatures are deliberately deferred to the Android Keystore-backed MIRROR SEED milestone rather than being implied by the current code.

## Repository Status

This repository is the canonical architecture and implementation home for MIGI core. Documentation describes intended system behavior and boundaries; it does not claim that every described module is already implemented or production-ready.

## License

This repository is licensed under the [Apache License 2.0](LICENSE).

## Contributing and Security

- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## Design Boundary

MIGI may analyze, recommend, simulate, and prepare actions. It does not treat a simulation as verified reality or perform consequential external or physical actions without an explicit authority path.
