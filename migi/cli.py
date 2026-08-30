from __future__ import annotations

import argparse
import json
from pathlib import Path

from .code_memory import CodeMemory, CodeSource
from .genesis import GenesisNode


def _print(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(prog="migi-genesis")
    parser.add_argument("--db", default=".migi/genesis.db", help="SQLite ChainLog path")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cmd = sub.add_parser("inspect", help="Inspect and receipt a local artifact")
    inspect_cmd.add_argument("path")
    inspect_cmd.add_argument("--actor", default="local-user")
    inspect_cmd.add_argument("--scope", default="local.read")

    recall_cmd = sub.add_parser("recall", help="Reconstruct artifact history from receipts")
    recall_cmd.add_argument("reference", help="Artifact ID, SHA-256, path, or filename")

    code_import = sub.add_parser("code-import", help="Import fenced code from a chat/log/Markdown file")
    code_import.add_argument("path")
    code_import.add_argument("--source-kind", default="file", choices=["chat", "log", "repository", "file", "generated", "external"])
    code_import.add_argument("--source-uri")
    code_import.add_argument("--status", default="prototype", choices=["concept", "specification", "prototype", "executable", "tested", "deprecated"])
    code_import.add_argument("--system", action="append", default=[])
    code_import.add_argument("--tag", action="append", default=[])
    code_import.add_argument("--revision")
    code_import.add_argument("--conversation-id")
    code_import.add_argument("--message-id")

    code_recall = sub.add_parser("code-recall", help="Search RAG0SHOT code memory")
    code_recall.add_argument("query")
    code_recall.add_argument("--language", action="append", default=[])
    code_recall.add_argument("--system", action="append", default=[])
    code_recall.add_argument("--source-kind", action="append", default=[])
    code_recall.add_argument("--limit", type=int, default=8)

    code_find = sub.add_parser("code-find", help="Find a code artifact by ID or exact SHA-256 content hash")
    code_find.add_argument("reference")

    sub.add_parser("verify", help="Verify the receipt hash chain")
    sub.add_parser("status", help="Show Genesis Node status")

    args = parser.parse_args()

    if args.command == "inspect":
        path = Path(args.path).expanduser().resolve()
        node = GenesisNode(args.db, allowed_roots=[path.parent])
        result = node.inspect_artifact(path, actor_id=args.actor, consent_scope=args.scope)
        _print(result)
        return 0 if result["authority"]["tre_logic"] == "+1" else 2

    node = GenesisNode(args.db, allowed_roots=[Path.cwd()])
    code_memory = CodeMemory(node.store)

    if args.command == "recall":
        result = node.recall_artifact(args.reference)
        _print(result)
        return 0 if result is not None else 1
    if args.command == "code-import":
        path = Path(args.path).expanduser().resolve()
        text = path.read_text(encoding="utf-8")
        source = CodeSource(
            kind=args.source_kind,
            uri=args.source_uri or f"file:{path}",
            path=str(path),
            revision=args.revision,
            conversation_id=args.conversation_id,
            message_id=args.message_id,
        )
        artifacts = code_memory.import_fenced_text(
            text,
            source=source,
            status=args.status,
            named_systems=args.system,
            tags=args.tag,
        )
        _print({"count": len(artifacts), "artifacts": artifacts})
        return 0
    if args.command == "code-recall":
        hits = code_memory.recall(
            args.query,
            languages=args.language,
            named_systems=args.system,
            source_kinds=args.source_kind,
            limit=max(1, args.limit),
        )
        _print({"query": args.query, "hits": hits})
        return 0 if hits else 1
    if args.command == "code-find":
        result = code_memory.find_exact(args.reference)
        _print(result)
        return 0 if result is not None else 1
    if args.command == "verify":
        result = node.store.verify_chain()
        _print(result)
        return 0 if result["valid"] else 1
    if args.command == "status":
        result = node.status()
        result["capabilities"] = sorted(set(result.get("capabilities", [])) | {"code.import", "code.recall", "code.find"})
        _print(result)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
