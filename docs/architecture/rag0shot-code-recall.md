# RAG0SHOT Code Recall

> Status: experimental baseline

RAG0SHOT code recall gives MIGI one provenance-preserving memory format for code recovered from chats, logs, repository history, files, experiments, and generated work.

It is intentionally **polyglot for recall and adapter-gated for execution**.

## Core rule

```text
Recall != execution
```

MIGI may remember, compare, rank, cite, and explain any indexed code artifact. Running that artifact requires a separately approved runtime adapter, an authority decision, and an execution receipt.

## Historical format families

The current registry covers the recurring formats recovered from MIGI/Mogo-Lab work:

```text
Systems / low level:
  Rust, C, C++, Shell

Mobile / JVM:
  Kotlin, Java, Android NDK/JNI, Vulkan

AI / scientific / simulation:
  Python, Haskell, Fortran, Qiskit-tagged Python

Web / XR:
  TypeScript, JavaScript, HTML, CSS, React, Vite, Astro,
  Three.js, WebXR

Enterprise / data:
  SQL, COBOL, Ruby/Rails

Web3:
  Solidity, Web3.js-tagged JavaScript

Schemas / configuration / documentation:
  JSON, JSON Schema, YAML, TOML, Markdown

MIGI symbolic formats:
  Emoji A++, Emoji ASCII++, Tre Logic

Research/reference:
  Plank and future caller-defined language identifiers
```

The registry is open-ended. Unknown languages can still be indexed because `language` and `format` are string identifiers rather than a closed enum.

## Artifact pipeline

```text
Chat / Log / Repo / File / Generated Output
                 |
                 v
          snippet extraction
                 |
                 v
        MIGI Code Artifact v0
        - language
        - format
        - original content
        - source URI
        - path/revision/message refs
        - status
        - named system tags
        - symbols
        - runtime adapter (optional)
        - parent artifact
        - receipt
        - SHA-256 content hash
                 |
                 v
          RAG0SHOT index
                 |
        +--------+---------+
        |                  |
        v                  v
 exact/lexical       future vector/
 metadata recall     semantic recall
        |                  |
        +--------+---------+
                 v
          provenance rerank
                 |
                 v
        recalled code + source
                 |
                 v
        authority / Tre Logic
                 |
      optional runtime adapter
                 |
                 v
          execution receipt
```

## Recall tiers

### Tier 0 — identity recall

Look up exact artifact IDs, content hashes, receipt IDs, source paths, symbols, or known system names.

### Tier 1 — RAG0SHOT baseline

`migi-recall` currently performs deterministic lexical + metadata ranking across title, language, format, tags, named systems, symbols, and code content.

This is intentionally useful without an embedding model or network connection.

### Tier 2 — semantic retrieval

A future embedding/vector adapter may rank artifacts semantically. It must return the same `RecallHit` provenance envelope and must never replace the original source/hash.

### Tier 3 — graph / lineage recall

ChainLog, receipt parentage, code parentage, project relationships, and future graph storage can expand a hit into its lineage:

```text
original snippet
 -> revision
 -> transpiled form
 -> executable form
 -> test result
 -> receipt
```

## Execution adapters

A `runtime_adapter` is a capability reference, not permission to run code.

Examples:

```text
rust        -> rust-cargo
python      -> python
cpp         -> native-cpp
kotlin      -> android-gradle
typescript  -> node
javascript  -> node-or-browser
csharp      -> dotnet-or-unity
solidity    -> evm-toolchain
sql         -> database
emoji-a++   -> alchemy-compiler
tre-logic   -> tre-rule-engine
```

Before execution:

```text
Recall hit
 -> verify content hash
 -> resolve exact artifact/revision
 -> LUFITGuard / Tre Logic
 -> select runtime adapter
 -> execute in scoped environment
 -> record output
 -> issue MIGIReceipt
 -> append lineage
```

## Historical chat/log import contract

An importer should preserve the original code block exactly and wrap it in `migi-code-artifact.v0`.

For a chat-derived snippet, record when available:

```text
source.kind = chat
source.uri = stable conversation/export reference
source.conversation_id
source.message_id
language
format
named_systems
tags
status
```

For repository code, also record:

```text
source.kind = repository
source.uri = repository identifier
source.path
source.revision = commit SHA / tag / branch snapshot
```

For run logs or generated artifacts, use `log` or `generated` and link `parent_artifact_id` / `receipt_id` whenever known.

## Storage

The first implementation supports newline-delimited JSON (`JSONL`) so artifacts are inspectable, diffable, and portable.

Later stores may include SQLite/ChainLog for local persistence and graph/vector projections for advanced retrieval. Those projections must never become the sole copy of provenance.

## Safety and provenance invariants

1. Preserve original code content.
2. Hash every artifact.
3. Require a source reference.
4. Distinguish concept/specification/prototype/executable/tested/deprecated.
5. Recall does not imply correctness.
6. Recall does not imply authorization.
7. Transpilation creates a child artifact; it never overwrites the original.
8. Execution requires an approved adapter and authority path.
9. Executions produce receipts and lineage.
10. Semantic/vector indexes are projections; source artifacts remain canonical.
