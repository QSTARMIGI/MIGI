from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    if args.command == "recall":
        result = node.recall_artifact(args.reference)
        _print(result)
        return 0 if result is not None else 1
    if args.command == "verify":
        result = node.store.verify_chain()
        _print(result)
        return 0 if result["valid"] else 1
    if args.command == "status":
        _print(node.status())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
