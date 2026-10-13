import unittest

from migi.mirrorfield.schema import Observation, ObservationKind, SourceClass
from migi.mirrorfield.sensors import TimedReference, align_pair
from migi.mirrorfield.state import build_state
from migi.mirrorfield.reflect import compare_numeric_features
from migi.mirrorfield.receipts import make_receipt, verify_receipt


DIGEST = "a" * 64


class MirrorfieldV0Tests(unittest.TestCase):
    def observation(self, observation_id, kind, timestamp, clock="device-clock"):
        return Observation(
            observation_id=observation_id,
            kind=kind,
            source_class=SourceClass.OBSERVED,
            timestamp_ns=timestamp,
            clock_id=clock,
            payload_ref=f"blob:{observation_id}",
            content_sha256=DIGEST,
        )

    def test_state_orders_observations_deterministically(self):
        a = self.observation("audio-1", ObservationKind.AUDIO, 20)
        v = self.observation("video-1", ObservationKind.VISUAL, 10)
        state = build_state("state-1", 25, [a, v])
        self.assertEqual([x.observation_id for x in state.observations],
                         ["video-1", "audio-1"])

    def test_state_rejects_duplicate_ids(self):
        a = self.observation("same", ObservationKind.AUDIO, 20)
        with self.assertRaises(ValueError):
            build_state("state-1", 25, [a, a])

    def test_alignment_requires_shared_clock_domain(self):
        left = TimedReference("audio", 100, "clock-a", "a")
        right = TimedReference("video", 105, "clock-b", "b")
        result = align_pair(left, right, 10)
        self.assertFalse(result.comparable)
        self.assertEqual(result.reason, "clock_domain_mismatch")

    def test_alignment_within_tolerance(self):
        left = TimedReference("audio", 100, "clock-a", "a")
        right = TimedReference("video", 105, "clock-a", "b")
        result = align_pair(left, right, 10)
        self.assertTrue(result.comparable)
        self.assertEqual(result.delta_ns, 5)

    def test_residual_metrics(self):
        result = compare_numeric_features([1.0, 2.0], [0.5, 2.0])
        self.assertEqual(result.feature_count, 2)
        self.assertEqual(result.mae_micro_units, 250000)
        self.assertEqual(result.mse_micro_units_squared, 125000000000)
        self.assertEqual(result.max_abs_micro_units, 500000)

    def test_residual_rejects_mismatched_vectors(self):
        with self.assertRaises(ValueError):
            compare_numeric_features([1.0], [1.0, 2.0])

    def test_receipt_verifies_and_detects_tampering(self):
        receipt = make_receipt(
            event_id="event-1", source_class="derived",
            input_refs=["observation-1"], output_ref="state-1",
            created_at_ns=123,
        )
        self.assertTrue(verify_receipt(receipt))
        tampered = dict(receipt, output_ref="state-2")
        self.assertFalse(verify_receipt(tampered))

    def test_receipt_hashes_are_deterministic(self):
        kwargs = dict(
            event_id="event-1", source_class="observed",
            input_refs=["audio-1", "video-1"], output_ref="state-1",
            created_at_ns=123,
        )
        self.assertEqual(make_receipt(**kwargs), make_receipt(**kwargs))


if __name__ == "__main__":
    unittest.main()
