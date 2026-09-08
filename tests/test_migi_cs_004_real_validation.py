from __future__ import annotations

import unittest

from benchmarks.migi_cs_004_real_validation import (
    ARTIFACT_PATHS,
    QUERY_CASES,
    load_artifacts,
    run_validation,
)


class MIGICS004RealValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_validation()

    def test_repository_corpus_uses_real_current_files(self):
        corpus = self.result["corpus"]
        self.assertTrue(corpus["repository_grounded"])
        self.assertFalse(corpus["weights_tuned_on_this_corpus"])
        self.assertEqual(corpus["artifact_count"], len(ARTIFACT_PATHS))
        self.assertEqual(len(corpus["corpus_sha256"]), 64)
        self.assertEqual(set(corpus["artifact_sha256"]), set(ARTIFACT_PATHS))
        self.assertTrue(all(len(value) == 64 for value in corpus["artifact_sha256"].values()))
        self.assertEqual(len(load_artifacts()), len(ARTIFACT_PATHS))

    def test_every_gold_target_is_in_candidate_corpus(self):
        corpus = set(ARTIFACT_PATHS)
        self.assertTrue(QUERY_CASES)
        for _, relevant_path in QUERY_CASES:
            self.assertIn(relevant_path, corpus)

    def test_retrieval_variants_emit_valid_metrics(self):
        retrieval = self.result["retrieval"]
        self.assertEqual(retrieval["cases"], len(QUERY_CASES))
        expected = {
            "semantic_only",
            "full",
            "without_provenance",
            "without_reliability",
            "without_graph",
            "without_temporal",
        }
        self.assertEqual(set(retrieval["variants"]), expected)
        for metrics in retrieval["variants"].values():
            for name in ("precision_at_1", "recall_at_3", "mrr"):
                self.assertGreaterEqual(metrics[name], 0.0)
                self.assertLessEqual(metrics[name], 1.0)

    def test_neutral_temporal_signal_cannot_change_ranking_metrics(self):
        variants = self.result["retrieval"]["variants"]
        self.assertEqual(variants["full"], variants["without_temporal"])

    def test_noise_degrades_to_unresolved_before_wrong_polarity(self):
        levels = self.result["noisy_evidence"]["noise_levels"]
        for level in ("0", "2", "4"):
            self.assertEqual(levels[level]["correct_polarity_rate"], 1.0)
            self.assertEqual(levels[level]["wrong_polarity_rate"], 0.0)
        self.assertEqual(levels["8"]["correct_polarity_rate"], 0.0)
        self.assertEqual(levels["8"]["unresolved_rate"], 1.0)
        self.assertEqual(levels["8"]["wrong_polarity_rate"], 0.0)
        self.assertEqual(levels["8"]["safe_or_correct_rate"], 1.0)

    def test_balanced_direct_conflict_becomes_unresolved(self):
        self.assertEqual(self.result["noisy_evidence"]["balanced_conflict_unresolved_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
