from __future__ import annotations

import argparse
import json
from pathlib import Path

from .code_memory import CodeMemory, CodeSource
from .genesis import GenesisNode
from .mirror_seed import MirrorSeed, verify_bundle


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

    capture_cmd = sub.add_parser("mirror-capture", help="Preserve an original selected file (8 MiB maximum)")
    capture_cmd.add_argument("path")
    capture_cmd.add_argument("--scope", default="", help="Explicitly use local.capture to authorize")
    analyze_cmd = sub.add_parser("mirror-analyze", help="Create a derived UTF-8 text analysis")
    analyze_cmd.add_argument("reference", help="Original artifact ID")
    analyze_cmd.add_argument("--scope", default="", help="Explicitly use local.analyze to authorize")
    history_cmd = sub.add_parser("mirror-history", help="Verify and recall selected artifact lineage")
    history_cmd.add_argument("reference")
    export_cmd = sub.add_parser("mirror-export", help="Prepare a selected-history bundle in a new local file")
    export_cmd.add_argument("reference", help="Derived artifact ID")
    export_cmd.add_argument("path", help="New output file; existing files are never overwritten")
    export_cmd.add_argument("--scope", default="", help="Explicitly use local.export to authorize")
    export_cmd.add_argument("--include-original", action="store_true", help="Explicitly include original bytes")
    bundle_cmd = sub.add_parser("mirror-verify", help="Verify a portable bundle without opening a database")
    bundle_cmd.add_argument("path")
    bundle_cmd.add_argument("--expected-export-hash", help="Independently retained export receipt hash")

    args = parser.parse_args()

    if args.command.startswith("mirror-"):
        try:
            if args.command == "mirror-verify":
                with Path(args.path).open("rb") as stream:
                    raw = stream.read(24 * 1024 * 1024 + 1)
                if len(raw) > 24 * 1024 * 1024:
                    raise ValueError("bundle_exceeds_24_mib")
                result = verify_bundle(json.loads(raw), expected_export_hash=args.expected_export_hash)
                _print(result)
                return 0 if result["valid"] else 1
            roots = [Path(args.path).expanduser().resolve().parent] if args.command == "mirror-capture" else [Path.cwd()]
            mirror = MirrorSeed(args.db, allowed_roots=roots)
            if args.command == "mirror-capture":
                result = mirror.capture(args.path, consent_scope=args.scope)
            elif args.command == "mirror-analyze":
                result = mirror.analyze(args.reference, consent_scope=args.scope)
            elif args.command == "mirror-history":
                _print(mirror.history(args.reference))
                return 0
            else:
                result = mirror.export(args.reference, consent_scope=args.scope,
                                       include_original=args.include_original)
                bundle = result.pop("bundle", None)
                if bundle is not None:
                    # Export receipt records preparation, not delivery or sharing.
                    with Path(args.path).open("x", encoding="utf-8") as stream:
                        json.dump(bundle, stream, ensure_ascii=False, indent=2)
                    result["bundle_path"] = str(Path(args.path).resolve())
            _print(result)
            if result["authority"]["tre_logic"] != "+1":
                return 2
            return 0 if result["execution"]["success"] else 1
        except (OSError, ValueError) as exc:
            _print({"error": type(exc).__name__, "message": str(exc)})
            return 1

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
