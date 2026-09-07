from __future__ import annotations

import unittest

from benchmarks.migi_cs_002_benchmark import generate_corpus, run_benchmark


class MIGICS002BenchmarkTests(unittest.TestCase):
    def test_corpus_is_fixed_and_balanced(self):
        cases = generate_corpus(1000)
        self.assertEqual(len(cases), 1000)
        counts = {
            label: sum(case.expected_qualification == label for case in cases)
            for label in (
                "supported",
                "contradicted",
                "unresolved",
                "out_of_profile",
                "simulation_only",
            )
        }
        self.assertEqual(
            counts,
            {
                "supported": 200,
                "contradicted": 200,
                "unresolved": 200,
                "out_of_profile": 200,
                "simulation_only": 200,
            },
        )

    def test_benchmark_exposes_provenance_ranking_difference(self):
        result = run_benchmark(1000, receipt_sample_size=5)
        semantic = result["retrieval"]["semantic_only"]
        rag0shot = result["retrieval"]["rag0shot"]

        self.assertAlmostEqual(semantic["precision_at_1"], 0.25)
        self.assertAlmostEqual(semantic["mrr"], 0.625)
        self.assertAlmostEqual(semantic["bad_source_top1_rate"], 0.75)
        self.assertAlmostEqual(rag0shot["precision_at_1"], 1.0)
        self.assertAlmostEqual(rag0shot["mrr"], 1.0)
        self.assertAlmostEqual(rag0shot["bad_source_top1_rate"], 0.0)
        self.assertAlmostEqual(rag0shot["recall_at_3"], 1.0)

    def test_claim_qualification_and_boundaries_are_measured(self):
        result = run_benchmark(1000, receipt_sample_size=5)
        metrics = result["qualification"]

        self.assertAlmostEqual(metrics["qualification_accuracy"], 1.0)
        self.assertAlmostEqual(metrics["evidence_state_accuracy"], 1.0)
        self.assertLess(metrics["multiclass_brier"], 0.02)
        self.assertLess(metrics["top_class_calibration_error"], 0.10)
        self.assertAlmostEqual(metrics["out_of_profile_refusal_accuracy"], 1.0)
        self.assertAlmostEqual(metrics["simulation_boundary_accuracy"], 1.0)

    def test_receipt_sample_uses_real_chain(self):
        result = run_benchmark(25, receipt_sample_size=5)
        receipts = result["receipt_overhead"]
        self.assertEqual(receipts["sample_size"], 5)
        self.assertTrue(receipts["receipt_chain_valid"])
        self.assertEqual(receipts["receipt_chain_checked"], 5)
        self.assertGreater(receipts["mean_receipt_bytes"], 0)
        self.assertGreater(receipts["mean_end_to_end_ms"], 0)


if __name__ == "__main__":
    unittest.main()
