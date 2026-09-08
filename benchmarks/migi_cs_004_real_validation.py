from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from migi.epistemics import EvidenceItem, RetrievalSignals, evaluate_evidence

ROOT = Path(__file__).resolve().parents[1]

ARTIFACT_PATHS = (
    "migi/authority.py",
    "migi/cambus.py",
    "migi/canonical.py",
    "migi/claim_runtime.py",
    "migi/code_memory.py",
    "migi/epistemics.py",
    "migi/events.py",
    "migi/genesis.py",
    "migi/models.py",
    "migi/replay.py",
    "migi/storage.py",
    "migi/api.py",
    "migi/cli.py",
    "docs/adr/0001-authority-and-provenance.md",
    "docs/adr/0002-source-classification.md",
    "docs/adr/0003-repository-boundaries.md",
    "docs/architecture/cambus-replay-v0.2.md",
    "docs/architecture/genesis-node-v0.1.md",
    "docs/architecture/lufit-sfo-verifiable-core.md",
    "docs/architecture/repository-roles.md",
    "docs/roadmap/mirror-seed-mvp.md",
    "README.md",
    "Systems Design",
    "Rust runtime",
    "Mvp Stack",
)

QUERY_CASES = (
    ("explicit local read and reasoning consent LUFITGuard state patch policy", "migi/authority.py"),
    ("CAMbus length prefixed socket frame QoS maximum frame bytes", "migi/cambus.py"),
    ("deterministic canonical JSON reject floats chained SHA-256 hash", "migi/canonical.py"),
    ("qualify claim SFO evidence LUFIT profile derived receipt memory", "migi/claim_runtime.py"),
    ("polyglot code artifact import recall exact content hash provenance", "migi/code_memory.py"),
    ("Tre evidence entropy uncertainty RAG0SHOT weighted retrieval signals", "migi/epistemics.py"),
    ("MUEF lowercase namespaced event actor source class validation", "migi/events.py"),
    ("Genesis intent authority execution receipt memory artifact inspect state patch", "migi/genesis.py"),
    ("source classes observed derived simulated proposed authorized executed", "migi/models.py"),
    ("replay only executed authorized state patch events after chain verification", "migi/replay.py"),
    ("SQLite WAL receipt chain previous hash append verify chain head", "migi/storage.py"),
    ("FastAPI status execute receipts code import recall find endpoints", "migi/api.py"),
    ("command line status inspect recall code import code find", "migi/cli.py"),
    ("authority and provenance precede consequential execution models do not authorize", "docs/adr/0001-authority-and-provenance.md"),
    ("classification boundary observed derived simulated proposed authorized executed", "docs/adr/0002-source-classification.md"),
    ("repository boundaries source of truth generated outputs architectural decisions", "docs/adr/0003-repository-boundaries.md"),
    ("CAMbus replay remote receipt is not local authority deterministic state convergence", "docs/architecture/cambus-replay-v0.2.md"),
    ("Genesis Node accountable intent to receipt execution core architecture", "docs/architecture/genesis-node-v0.1.md"),
    ("LUFIT SFO verifiable claim core profile entropy simulation boundary", "docs/architecture/lufit-sfo-verifiable-core.md"),
    ("repository roles architecture documentation ownership and boundaries", "docs/architecture/repository-roles.md"),
    ("MIRROR SEED Pixel capture explain simulate prove MVP", "docs/roadmap/mirror-seed-mvp.md"),
)

PREDICATE_CASES = (
    ("migi/cambus.py", "MAX_FRAME_BYTES", True),
    ("migi/canonical.py", "allow_nan=False", True),
    ("migi/storage.py", "receipt_chain", True),
    ("migi/replay.py", "migi.state.patch", True),
    ("migi/events.py", "muef.v0", True),
    ("migi/authority.py", "local.reason", True),
    ("migi/api.py", "/code/recall", True),
    ("migi/code_memory.py", "class CodeMemory", True),
    ("migi/claim_runtime.py", "simulation_only", True),
    ("docs/adr/0001-authority-and-provenance.md", "Models may analyze", True),
    ("migi/cambus.py", "pickle.loads", False),
    ("migi/canonical.py", "orjson.dumps", False),
    ("migi/storage.py", "PostgreSQL", False),
    ("migi/replay.py", "apply denied receipt", False),
    ("migi/events.py", "kernel_actor", False),
    ("migi/authority.py", "payment.execute", False),
    ("migi/api.py", "/payments", False),
    ("migi/code_memory.py", "subprocess.run", False),
    ("migi/claim_runtime.py", "execute physical actuator", False),
    ("docs/adr/0001-authority-and-provenance.md", "models authorize payment execution", False),
)

CURRENT_WEIGHTS = {
    "semantic": 0.40,
    "provenance": 0.20,
    "reliability": 0.15,
    "graph": 0.15,
    "temporal": 0.10,
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "with", "without", "only", "after",
}


@dataclass(frozen=True)
class Artifact:
    path: str
    text: str
    digest: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    relevant_path: str


@dataclass(frozen=True)
class RankedArtifact:
    path: str
    score: float
    signals: RetrievalSignals


def _tokenize(value: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    expanded = expanded.replace("_", " ").replace("/", " ").replace("-", " ").replace(".", " ")
    return [
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9+]+", expanded)
        if len(token) > 1 and token.casefold() not in STOPWORDS
    ]


def load_artifacts(root: Path = ROOT) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for relative in ARTIFACT_PATHS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"MIGI-CS-004 artifact missing: {relative}")
        text = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        path_tokens = _tokenize(relative) * 4
        artifacts.append(
            Artifact(
                path=relative,
                text=text,
                digest=digest,
                tokens=tuple(path_tokens + _tokenize(text)),
            )
        )
    return artifacts


def corpus_digest(artifacts: Iterable[Artifact]) -> str:
    material = "\n".join(f"{artifact.path}:{artifact.digest}" for artifact in sorted(artifacts, key=lambda item: item.path))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _tfidf_semantic_scores(query: str, artifacts: list[Artifact]) -> dict[str, float]:
    document_counts = [Counter(artifact.tokens) for artifact in artifacts]
    query_counts = Counter(_tokenize(query))
    document_frequency: Counter[str] = Counter()
    for counts in document_counts:
        for token in counts:
            document_frequency[token] += 1

    count = len(artifacts)

    def idf(token: str) -> float:
        return math.log((count + 1.0) / (document_frequency.get(token, 0) + 1.0)) + 1.0

    query_vector = {token: frequency * idf(token) for token, frequency in query_counts.items()}
    query_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1.0
    raw: dict[str, float] = {}

    for artifact, counts in zip(artifacts, document_counts):
        overlap = set(query_vector).intersection(counts)
        dot = sum(query_vector[token] * (counts[token] * idf(token)) for token in overlap)
        doc_norm = math.sqrt(sum((frequency * idf(token)) ** 2 for token, frequency in counts.items())) or 1.0
        raw[artifact.path] = dot / (query_norm * doc_norm)

    maximum = max(raw.values(), default=0.0)
    if maximum <= 0.0:
        return {path: 0.0 for path in raw}
    return {path: value / maximum for path, value in raw.items()}


def _path_quality(path: str) -> tuple[float, float]:
    if path.startswith("migi/") and path.endswith(".py"):
        return 1.0, 0.95
    if path.startswith("docs/adr/"):
        return 0.95, 0.95
    if path.startswith("docs/architecture/"):
        return 0.90, 0.85
    if path.startswith("docs/roadmap/"):
        return 0.85, 0.80
    if path == "README.md":
        return 0.75, 0.70
    return 0.40, 0.45


def _import_graph(artifacts: list[Artifact]) -> dict[str, set[str]]:
    module_to_path = {
        Path(artifact.path).stem: artifact.path
        for artifact in artifacts
        if artifact.path.startswith("migi/") and artifact.path.endswith(".py")
    }
    graph: dict[str, set[str]] = defaultdict(set)

    for artifact in artifacts:
        if not artifact.path.startswith("migi/") or not artifact.path.endswith(".py"):
            continue
        for module in re.findall(r"^from \.([A-Za-z0-9_]+) import ", artifact.text, flags=re.MULTILINE):
            target = module_to_path.get(module)
            if target:
                graph[artifact.path].add(target)
                graph[target].add(artifact.path)
        for module in re.findall(r"^import migi\.([A-Za-z0-9_]+)", artifact.text, flags=re.MULTILINE):
            target = module_to_path.get(module)
            if target:
                graph[artifact.path].add(target)
                graph[target].add(artifact.path)
    return graph


def _signals_for_query(query: str, artifacts: list[Artifact]) -> dict[str, RetrievalSignals]:
    semantic = _tfidf_semantic_scores(query, artifacts)
    graph = _import_graph(artifacts)
    signals: dict[str, RetrievalSignals] = {}

    for artifact in artifacts:
        provenance, reliability = _path_quality(artifact.path)
        neighbors = graph.get(artifact.path, set())
        graph_score = max((semantic.get(neighbor, 0.0) for neighbor in neighbors), default=0.0)
        signals[artifact.path] = RetrievalSignals(
            semantic=semantic[artifact.path],
            provenance=provenance,
            reliability=reliability,
            graph=graph_score,
            # CI has a shallow checkout and no stable per-file timestamp source.
            # Keep temporal neutral so the ablation can honestly show whether it matters here.
            temporal=0.50,
        )
    return signals


def _normalized_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0.0:
        raise ValueError("retrieval weights must contain positive mass")
    return {name: value / total for name, value in weights.items()}


def _score(signals: RetrievalSignals, weights: dict[str, float]) -> float:
    normalized = _normalized_weights(weights)
    return sum(normalized[name] * float(getattr(signals, name)) for name in normalized)


def rank_query(query: str, artifacts: list[Artifact], weights: dict[str, float]) -> list[RankedArtifact]:
    signals = _signals_for_query(query, artifacts)
    ranked = [RankedArtifact(path=path, score=_score(value, weights), signals=value) for path, value in signals.items()]
    return sorted(ranked, key=lambda item: (-item.score, item.path))


def _retrieval_metrics(cases: Iterable[RetrievalCase], artifacts: list[Artifact], weights: dict[str, float]) -> dict[str, float]:
    reciprocal_ranks: list[float] = []
    top1 = 0
    recall_at_3 = 0
    for case in cases:
        ranking = rank_query(case.query, artifacts, weights)
        paths = [item.path for item in ranking]
        position = paths.index(case.relevant_path) + 1
        reciprocal_ranks.append(1.0 / position)
        top1 += position == 1
        recall_at_3 += position <= 3
    count = len(tuple(cases)) if not isinstance(cases, tuple) else len(cases)
    return {
        "precision_at_1": top1 / count,
        "recall_at_3": recall_at_3 / count,
        "mrr": statistics.fmean(reciprocal_ranks),
    }


def _ablation_weights() -> dict[str, dict[str, float]]:
    variants = {
        "semantic_only": {"semantic": 1.0, "provenance": 0.0, "reliability": 0.0, "graph": 0.0, "temporal": 0.0},
        "full": dict(CURRENT_WEIGHTS),
    }
    for removed in ("provenance", "reliability", "graph", "temporal"):
        weights = dict(CURRENT_WEIGHTS)
        weights[removed] = 0.0
        variants[f"without_{removed}"] = weights
    return variants


def run_retrieval_validation(artifacts: list[Artifact]) -> dict[str, Any]:
    cases = tuple(RetrievalCase(query=query, relevant_path=path) for query, path in QUERY_CASES)
    variants = {
        name: _retrieval_metrics(cases, artifacts, weights)
        for name, weights in _ablation_weights().items()
    }
    full = variants["full"]
    ablation_delta = {
        name: {
            metric: values[metric] - full[metric]
            for metric in ("precision_at_1", "recall_at_3", "mrr")
        }
        for name, values in variants.items()
        if name not in {"full", "semantic_only"}
    }
    return {
        "cases": len(cases),
        "variants": variants,
        "ablation_delta_vs_full": ablation_delta,
    }


def _direct_evidence(expected_present: bool) -> EvidenceItem:
    return EvidenceItem(
        direction=1.0 if expected_present else -1.0,
        confidence=0.99,
        reliability=0.99,
        provenance_quality=1.0,
    )


def _noise_item(expected_present: bool) -> EvidenceItem:
    return EvidenceItem(
        direction=-1.0 if expected_present else 1.0,
        confidence=0.50,
        reliability=0.35,
        provenance_quality=0.25,
    )


def run_noisy_evidence_validation(root: Path = ROOT) -> dict[str, Any]:
    noise_levels = (0, 2, 4, 8)
    per_level: dict[str, dict[str, float]] = {}
    balanced_conflicts = 0
    balanced_unresolved = 0

    predicates: list[tuple[str, bool, bool]] = []
    for path, needle, expected in PREDICATE_CASES:
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        actual = needle in text
        predicates.append((f"{path}::{needle}", expected, actual))
        if actual != expected:
            raise AssertionError(f"real-data predicate drifted: {path!r} contains {needle!r} => {actual}, expected {expected}")

    for level in noise_levels:
        correct = 0
        unresolved = 0
        wrong = 0
        uncertainty: list[float] = []
        for _, expected, _ in predicates:
            evidence = [_direct_evidence(expected)] + [_noise_item(expected) for _ in range(level)]
            assessment = evaluate_evidence(evidence)
            expected_state = "+1" if expected else "-1"
            if assessment.state == expected_state:
                correct += 1
            elif assessment.state == "0":
                unresolved += 1
            else:
                wrong += 1
            uncertainty.append(assessment.uncertainty)

        total = len(predicates)
        per_level[str(level)] = {
            "correct_polarity_rate": correct / total,
            "unresolved_rate": unresolved / total,
            "wrong_polarity_rate": wrong / total,
            "safe_or_correct_rate": (correct + unresolved) / total,
            "mean_uncertainty": statistics.fmean(uncertainty),
        }

    # Equal-strength direct contradiction should become unresolved rather than flip polarity.
    for _, expected, _ in predicates:
        direct = _direct_evidence(expected)
        opposite = EvidenceItem(
            direction=-direct.direction,
            confidence=direct.confidence,
            reliability=direct.reliability,
            provenance_quality=direct.provenance_quality,
        )
        assessment = evaluate_evidence([direct, opposite])
        balanced_conflicts += 1
        balanced_unresolved += assessment.state == "0"

    return {
        "predicate_cases": len(predicates),
        "noise_levels": per_level,
        "balanced_conflict_unresolved_rate": balanced_unresolved / balanced_conflicts,
    }


def run_validation(root: Path = ROOT) -> dict[str, Any]:
    artifacts = load_artifacts(root)
    return {
        "benchmark": "MIGI-CS-004",
        "corpus": {
            "repository_grounded": True,
            "artifact_count": len(artifacts),
            "artifact_paths": [artifact.path for artifact in artifacts],
            "corpus_sha256": corpus_digest(artifacts),
            "artifact_sha256": {artifact.path: artifact.digest for artifact in artifacts},
            "weights_tuned_on_this_corpus": False,
        },
        "retrieval": run_retrieval_validation(artifacts),
        "noisy_evidence": run_noisy_evidence_validation(root),
        "interpretation": (
            "Repository-grounded validation on the current MIGI source/docs snapshot. "
            "Gold retrieval targets are manually labeled, weights were fixed before this corpus, "
            "and temporal relevance is neutral because CI has no stable per-file timestamp source. "
            "This is stronger than the synthetic contract benchmark but is not external real-world validation."
        ),
    }


def _human_report(result: dict[str, Any]) -> str:
    variants = result["retrieval"]["variants"]
    noise = result["noisy_evidence"]["noise_levels"]
    lines = [
        f"{result['benchmark']} repository-grounded validation",
        f"artifacts={result['corpus']['artifact_count']} corpus_sha256={result['corpus']['corpus_sha256']}",
    ]
    for name in ("semantic_only", "full", "without_provenance", "without_reliability", "without_graph", "without_temporal"):
        value = variants[name]
        lines.append(
            f"{name}: P@1={value['precision_at_1']:.3f} R@3={value['recall_at_3']:.3f} MRR={value['mrr']:.3f}"
        )
    for level in ("0", "2", "4", "8"):
        value = noise[level]
        lines.append(
            f"noise={level}: correct={value['correct_polarity_rate']:.3f} unresolved={value['unresolved_rate']:.3f} "
            f"wrong={value['wrong_polarity_rate']:.3f} uncertainty={value['mean_uncertainty']:.3f}"
        )
    lines.append(
        f"balanced-conflict unresolved={result['noisy_evidence']['balanced_conflict_unresolved_rate']:.3f}"
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MIGI-CS-004 repository-grounded validation")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    result = run_validation()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_human_report(result))


if __name__ == "__main__":
    main()
