from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from migi.authority import LUFITGuard
from migi.claim_runtime import VerifiableClaimRuntime
from migi.epistemics import (
    ClaimRequirements,
    EvidenceItem,
    LUFITProfile,
    RetrievalSignals,
    SFOObservation,
    evaluate_evidence,
    qualify_factual_claim,
    rag0shot_score,
    validate_profile,
)
from migi.models import SourceClass
from migi.storage import GenesisStore

CORPUS_SIZE = 1000
RECEIPT_SAMPLE_SIZE = 20


@dataclass(frozen=True)
class RetrievalCandidate:
    candidate_id: str
    source_quality: str
    signals: RetrievalSignals


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    expected_qualification: str
    expected_evidence_state: str
    observation: SFOObservation
    evidence: tuple[EvidenceItem, ...]
    profile: LUFITProfile
    requirements: ClaimRequirements
    relevant_candidate_id: str
    retrieval_candidates: tuple[RetrievalCandidate, ...]


def generate_corpus(size: int = CORPUS_SIZE) -> list[BenchmarkCase]:
    """Generate the fixed synthetic MIGI-CS-002 contract corpus.

    The generator is intentionally deterministic and contains no random state.
    Five claim regimes repeat evenly: supported, contradicted, unresolved,
    out-of-profile, and simulation-only. Every case also contains a retrieval
    problem with one trusted relevant candidate plus distractors.
    """
    if size <= 0:
        raise ValueError("benchmark corpus size must be positive")

    cases: list[BenchmarkCase] = []
    for index in range(size):
        regime = index % 5
        case_id = f"migi-cs-002-{index:04d}"

        in_profile = LUFITProfile.create(
            resolution_level=1.0,
            budget_units=100,
            observables={"sensor", "provenance"},
            methods={"weighted-evidence"},
            cutoff=10.0,
        )
        normal_requirements = ClaimRequirements.create(
            required_resolution_level=0.8,
            estimated_cost_units=50,
            required_observables={"sensor"},
            method="weighted-evidence",
            regime_value=5.0,
        )

        if regime == 0:
            expected_qualification = "supported"
            expected_state = "+1"
            direction = 1.0
            source_class = SourceClass.OBSERVED.value
            profile = in_profile
            requirements = normal_requirements
        elif regime == 1:
            expected_qualification = "contradicted"
            expected_state = "-1"
            direction = -1.0
            source_class = SourceClass.OBSERVED.value
            profile = in_profile
            requirements = normal_requirements
        elif regime == 2:
            expected_qualification = "unresolved"
            expected_state = "0"
            direction = 0.0
            source_class = SourceClass.OBSERVED.value
            profile = in_profile
            requirements = normal_requirements
        elif regime == 3:
            expected_qualification = "out_of_profile"
            expected_state = "+1"
            direction = 1.0
            source_class = SourceClass.OBSERVED.value
            profile = in_profile
            requirements = ClaimRequirements.create(
                required_resolution_level=1.2,
                estimated_cost_units=150,
                required_observables={"sensor", "spectral"},
                method="spectral-inversion",
                regime_value=12.0,
            )
        else:
            expected_qualification = "simulation_only"
            expected_state = "+1"
            direction = 1.0
            source_class = SourceClass.SIMULATED.value
            profile = in_profile
            requirements = normal_requirements

        observation = SFOObservation(
            source_id=f"source-{index % 17:02d}",
            source_class=source_class,
            value={"case": case_id, "signal": round(0.5 + (index % 100) / 200.0, 4)},
            confidence=0.98,
            provenance_ref=f"receipt:fixture-{index:04d}",
        )
        evidence = (
            EvidenceItem(
                direction=direction,
                confidence=0.98,
                reliability=0.96,
                provenance_quality=0.95,
            ),
        )

        relevant_id = f"{case_id}:trusted"
        trusted_semantic = 0.86 + ((index % 7) - 3) * 0.005
        # On one quarter of cases semantic-only gets the trusted source right;
        # otherwise the low-provenance distractor is deliberately more similar.
        seductive_semantic = trusted_semantic - 0.02 if index % 4 == 0 else trusted_semantic + 0.08
        retrieval_candidates = (
            RetrievalCandidate(
                candidate_id=relevant_id,
                source_quality="trusted",
                signals=RetrievalSignals(
                    semantic=trusted_semantic,
                    provenance=0.95,
                    reliability=0.96,
                    graph=0.85,
                    temporal=0.80,
                ),
            ),
            RetrievalCandidate(
                candidate_id=f"{case_id}:seductive-untrusted",
                source_quality="bad",
                signals=RetrievalSignals(
                    semantic=min(seductive_semantic, 0.99),
                    provenance=0.05,
                    reliability=0.10,
                    graph=0.30,
                    temporal=0.90,
                ),
            ),
            RetrievalCandidate(
                candidate_id=f"{case_id}:medium",
                source_quality="medium",
                signals=RetrievalSignals(
                    semantic=0.63,
                    provenance=0.60,
                    reliability=0.65,
                    graph=0.55,
                    temporal=0.60,
                ),
            ),
            RetrievalCandidate(
                candidate_id=f"{case_id}:stale",
                source_quality="medium",
                signals=RetrievalSignals(
                    semantic=0.58,
                    provenance=0.80,
                    reliability=0.75,
                    graph=0.45,
                    temporal=0.10,
                ),
            ),
            RetrievalCandidate(
                candidate_id=f"{case_id}:noise",
                source_quality="bad",
                signals=RetrievalSignals(
                    semantic=0.30,
                    provenance=0.20,
                    reliability=0.20,
                    graph=0.15,
                    temporal=0.70,
                ),
            ),
        )

        cases.append(
            BenchmarkCase(
                case_id=case_id,
                expected_qualification=expected_qualification,
                expected_evidence_state=expected_state,
                observation=observation,
                evidence=evidence,
                profile=profile,
                requirements=requirements,
                relevant_candidate_id=relevant_id,
                retrieval_candidates=retrieval_candidates,
            )
        )
    return cases


def _rank_semantic(case: BenchmarkCase) -> list[RetrievalCandidate]:
    return sorted(
        case.retrieval_candidates,
        key=lambda candidate: (-candidate.signals.semantic, candidate.candidate_id),
    )


def _rank_rag0shot(case: BenchmarkCase) -> list[RetrievalCandidate]:
    return sorted(
        case.retrieval_candidates,
        key=lambda candidate: (-rag0shot_score(candidate.signals), candidate.candidate_id),
    )


def _retrieval_metrics(cases: list[BenchmarkCase], ranker) -> dict[str, float]:
    reciprocal_ranks: list[float] = []
    top1 = 0
    recall_at_3 = 0
    bad_top1 = 0

    for case in cases:
        ranking = ranker(case)
        ids = [candidate.candidate_id for candidate in ranking]
        position = ids.index(case.relevant_candidate_id) + 1
        reciprocal_ranks.append(1.0 / position)
        top1 += position == 1
        recall_at_3 += position <= 3
        bad_top1 += ranking[0].source_quality == "bad"

    count = len(cases)
    return {
        "precision_at_1": top1 / count,
        "recall_at_3": recall_at_3 / count,
        "mrr": statistics.fmean(reciprocal_ranks),
        "bad_source_top1_rate": bad_top1 / count,
    }


def _multiclass_brier(probabilities: tuple[float, float, float], expected_state: str) -> float:
    state_index = {"-1": 0, "0": 1, "+1": 2}[expected_state]
    target = [0.0, 0.0, 0.0]
    target[state_index] = 1.0
    return sum((probabilities[index] - target[index]) ** 2 for index in range(3))


def _qualification_metrics(cases: list[BenchmarkCase]) -> dict[str, Any]:
    correct = 0
    state_correct = 0
    brier_scores: list[float] = []
    confidences: list[float] = []
    correctness: list[float] = []
    out_profile_total = 0
    out_profile_correct = 0
    simulation_total = 0
    simulation_correct = 0
    latencies_ms: list[float] = []

    for case in cases:
        started = time.perf_counter()
        assessment = evaluate_evidence(case.evidence)
        profile_status = validate_profile(case.profile, case.requirements)
        qualification = qualify_factual_claim(
            source_class=case.observation.source_class,
            profile_status=profile_status,
            assessment=assessment,
        )
        latencies_ms.append((time.perf_counter() - started) * 1000.0)

        is_correct = qualification == case.expected_qualification
        correct += is_correct
        state_correct += assessment.state == case.expected_evidence_state

        if case.expected_qualification in {"supported", "contradicted", "unresolved"}:
            brier_scores.append(_multiclass_brier(assessment.probabilities, case.expected_evidence_state))
            predicted_confidence = max(assessment.probabilities)
            confidences.append(predicted_confidence)
            correctness.append(1.0 if assessment.state == case.expected_evidence_state else 0.0)

        if case.expected_qualification == "out_of_profile":
            out_profile_total += 1
            out_profile_correct += qualification == "out_of_profile"
        if case.expected_qualification == "simulation_only":
            simulation_total += 1
            simulation_correct += qualification == "simulation_only"

    return {
        "qualification_accuracy": correct / len(cases),
        "evidence_state_accuracy": state_correct / len(cases),
        "multiclass_brier": statistics.fmean(brier_scores),
        "top_class_calibration_error": abs(statistics.fmean(confidences) - statistics.fmean(correctness)),
        "out_of_profile_refusal_accuracy": out_profile_correct / out_profile_total,
        "simulation_boundary_accuracy": simulation_correct / simulation_total,
        "latency_ms": {
            "p50": _percentile(latencies_ms, 0.50),
            "p95": _percentile(latencies_ms, 0.95),
            "mean": statistics.fmean(latencies_ms),
        },
    }


def _receipt_metrics(cases: list[BenchmarkCase], sample_size: int = RECEIPT_SAMPLE_SIZE) -> dict[str, Any]:
    selected = cases[: max(1, min(sample_size, len(cases)))]
    receipt_bytes: list[int] = []
    execution_ms: list[float] = []

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        store = GenesisStore(root / "benchmark.db")
        guard = LUFITGuard([root])
        runtime = VerifiableClaimRuntime(store, guard)

        for case in selected:
            started = time.perf_counter()
            result = runtime.qualify_claim(
                case.case_id,
                state_before={"phase": "before"},
                state_after={"phase": "after"},
                observation=case.observation,
                evidence=case.evidence,
                profile=case.profile,
                requirements=case.requirements,
            )
            execution_ms.append((time.perf_counter() - started) * 1000.0)
            encoded = json.dumps(result["receipt"], sort_keys=True, separators=(",", ":")).encode("utf-8")
            receipt_bytes.append(len(encoded))

        chain = store.verify_chain()

    return {
        "sample_size": len(selected),
        "mean_receipt_bytes": statistics.fmean(receipt_bytes),
        "p95_receipt_bytes": _percentile([float(value) for value in receipt_bytes], 0.95),
        "mean_end_to_end_ms": statistics.fmean(execution_ms),
        "p95_end_to_end_ms": _percentile(execution_ms, 0.95),
        "receipt_chain_valid": bool(chain["valid"]),
        "receipt_chain_checked": int(chain["checked"]),
    }


def run_benchmark(size: int = CORPUS_SIZE, receipt_sample_size: int = RECEIPT_SAMPLE_SIZE) -> dict[str, Any]:
    cases = generate_corpus(size)
    semantic = _retrieval_metrics(cases, _rank_semantic)
    rag0shot = _retrieval_metrics(cases, _rank_rag0shot)
    qualification = _qualification_metrics(cases)
    receipts = _receipt_metrics(cases, receipt_sample_size)

    return {
        "benchmark": "MIGI-CS-002",
        "corpus": {
            "size": len(cases),
            "regimes": {
                label: sum(case.expected_qualification == label for case in cases)
                for label in (
                    "supported",
                    "contradicted",
                    "unresolved",
                    "out_of_profile",
                    "simulation_only",
                )
            },
            "synthetic": True,
            "deterministic": True,
        },
        "retrieval": {
            "semantic_only": semantic,
            "rag0shot": rag0shot,
            "delta": {
                "precision_at_1": rag0shot["precision_at_1"] - semantic["precision_at_1"],
                "mrr": rag0shot["mrr"] - semantic["mrr"],
                "bad_source_top1_rate": rag0shot["bad_source_top1_rate"] - semantic["bad_source_top1_rate"],
            },
        },
        "qualification": qualification,
        "receipt_overhead": receipts,
        "interpretation": (
            "Synthetic contract benchmark only. It tests the intended architecture under controlled failure modes; "
            "it is not evidence of real-world generalization or superiority."
        ),
    }


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _human_report(result: dict[str, Any]) -> str:
    retrieval = result["retrieval"]
    qualification = result["qualification"]
    receipts = result["receipt_overhead"]
    return "\n".join(
        [
            f"{result['benchmark']} synthetic benchmark ({result['corpus']['size']} cases)",
            f"semantic P@1={retrieval['semantic_only']['precision_at_1']:.3f} MRR={retrieval['semantic_only']['mrr']:.3f} bad-top1={retrieval['semantic_only']['bad_source_top1_rate']:.3f}",
            f"RAG0SHOT P@1={retrieval['rag0shot']['precision_at_1']:.3f} MRR={retrieval['rag0shot']['mrr']:.3f} bad-top1={retrieval['rag0shot']['bad_source_top1_rate']:.3f}",
            f"qualification accuracy={qualification['qualification_accuracy']:.3f} Brier={qualification['multiclass_brier']:.6f} calibration-error={qualification['top_class_calibration_error']:.6f}",
            f"out-of-profile refusal={qualification['out_of_profile_refusal_accuracy']:.3f} simulation-boundary={qualification['simulation_boundary_accuracy']:.3f}",
            f"pure qualification latency p50={qualification['latency_ms']['p50']:.4f}ms p95={qualification['latency_ms']['p95']:.4f}ms",
            f"receipt sample={receipts['sample_size']} mean-bytes={receipts['mean_receipt_bytes']:.1f} end-to-end p95={receipts['p95_end_to_end_ms']:.3f}ms chain-valid={receipts['receipt_chain_valid']}",
            result["interpretation"],
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic MIGI-CS-002 benchmark")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the human summary")
    parser.add_argument("--size", type=int, default=CORPUS_SIZE)
    parser.add_argument("--receipt-sample", type=int, default=RECEIPT_SAMPLE_SIZE)
    args = parser.parse_args()

    result = run_benchmark(args.size, args.receipt_sample)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_human_report(result))


if __name__ == "__main__":
    main()
