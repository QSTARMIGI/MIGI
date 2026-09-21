"""Run the public-sample MS-001 workflow. No real device capture is implied.

From repository root: PYTHONPATH=. python examples/mirror_seed_demo.py --output .migi/demo.json
"""
import argparse
import json
from pathlib import Path
import tempfile

from migi.mirror_seed import MirrorSeed, verify_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="New local bundle file")
    args = parser.parse_args()
    output = Path(args.output)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        sample = root / "sample.txt"
        sample.write_text("MIGI MIRROR SEED\nOne original. One approved transformation.\n", encoding="utf-8")
        mirror = MirrorSeed(root / "genesis.db", allowed_roots=[root])
        capture = mirror.capture(sample, consent_scope="local.capture")
        sample.unlink()
        derived = mirror.analyze(capture["artifact"]["artifact_id"], consent_scope="local.analyze")
        export = mirror.export(derived["artifact"]["artifact_id"], consent_scope="local.export", include_original=True)
        bundle = export["bundle"]
        chain = mirror.store.verify_chain()
    # Verification occurs after the source, database, and temporary directory are gone.
    check = verify_bundle(bundle, expected_export_hash=export["receipt_hash"])
    if not check["valid"] or not chain["valid"]:
        raise RuntimeError("demo verification failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(bundle, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"milestone": "MS-001 offline core", "bundle": str(output),
                      "receipt_chain": chain, "verification": check}, indent=2))


if __name__ == "__main__":
    main()
