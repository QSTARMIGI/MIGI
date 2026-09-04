from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from migi.claim_runtime import VerifiableClaimRuntime
from migi.epistemics import (
    ClaimRequirements,
    EvidenceItem,
    EvidenceState,
    LUFITProfile,
    RetrievalSignals,
    SFOObservation,
    evaluate_evidence,
    rag0shot_score,
)
from migi.genesis import GenesisNode
from migi.models import SourceClass


class EpistemicsTests(unittest.TestCase):
    def _runtime(self, root: Path) -> tuple[GenesisNode, VerifiableClaimRuntime]:
        node = GenesisNode(root / "genesis.db", allowed_roots=[root])
        return node, VerifiableClaimRuntime(node.store, node.guard)

    def _profile(self) -> LUFITProfile:
        return LUFITProfile.create(
            resolution_level=64.0,
            budget_units=1_000,
            observables=["temperature"],
            methods=["sensor-fusion"],
            cutoff=10.0,
        )

    def _requirements(self) -> ClaimRequirements:
        return ClaimRequirements.create(
            required_resolution_level=32.0,
            estimated_cost_units=100,
            required_observables=["temperature"],
            method="sensor-fusion",
            regime_value=2.0,
        )

    def _evidence(self) -> list[EvidenceItem]:
        return [
            EvidenceItem(1.0, 0.98, 0.95, 1.0),
            EvidenceItem(0.9, 0.90, 0.90, 0.90),
            EvidenceItem(-1.0, 0.80, 0.20, 0.20),
        ]

    def test_no_evidence_is_unresolved_and_maximally_uncertain(self):
        result = evaluate_evidence([], threshold=0.60)
        self.assertEqual(result.state, EvidenceState.UNRESOLVED.value)
        self.assertAlmostEqual(result.uncertainty, 1.0)

    def test_observation_to_receipt_to_recall_to_qualified_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            node, runtime = self._runtime(root)
            assessment = evaluate_evidence(self._evidence(), threshold=0.60)
            self.assertEqual(assessment.state, EvidenceState.SUPPORTED.value)

            result = runtime.qualify_claim(
                "engine.temperature.nominal",
                state_before={"mode": "sampling"},
                state_after={"mode": "qualified"},
                observation=SFOObservation(
                    source_id="sensor-a",
                    source_class=SourceClass.OBSERVED.value,
                    value={"temperature_c": 21.5},
                    confidence=assessment.confidence,
                    provenance_ref="sensor:a:sample:1",
                ),
                evidence=self._evidence(),
                profile=self._profile(),
                requirements=self._requirements(),
                actor_id="tester",
            )

            self.assertEqual(result["authority"]["tre_logic"], "+1")
            self.assertEqual(result["execution"]["output"]["qualification"], "supported")
            self.assertEqual(result["receipt"]["source_class"], SourceClass.DERIVED.value)
            self.assertTrue(result["chain"]["valid"])
            self.assertEqual(result["chain"]["checked"], 1)

            recalled = runtime.recall_claim("engine.temperature.nominal")
            self.assertIsNotNone(recalled)
            self.assertTrue(recalled["chain"]["valid"])
            self.assertEqual(recalled["history"][0]["intent"]["action"], "claim.qualify")
            self.assertEqual(recalled["memories"][0]["facts"]["qualification"], "supported")
            self.assertEqual(node.store.verify_chain()["checked"], 1)

    def test_simulation_never_silently_becomes_observation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, runtime = self._runtime(root)
            result = runtime.qualify_claim(
                "sim.prediction",
                state_before={"mode": "simulation"},
                state_after={"mode": "simulation_complete"},
                observation=SFOObservation(
                    source_id="physics-sim",
                    source_class=SourceClass.SIMULATED.value,
                    value={"temperature_c": 103.0},
                    confidence=1.0,
                    provenance_ref="sim:run:1",
                ),
                evidence=[EvidenceItem(1.0, 1.0, 1.0, 1.0)],
                profile=self._profile(),
                requirements=self._requirements(),
            )

            self.assertEqual(result["execution"]["output"]["qualification"], "simulation_only")
            self.assertTrue(result["execution"]["verification"]["simulation_preserved"])

    def test_out_of_profile_claim_is_explicitly_refused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, runtime = self._runtime(root)
            profile = LUFITProfile.create(
                resolution_level=16.0,
                budget_units=25,
                observables=["camera"],
                methods=["vision"],
                cutoff=1.0,
            )
            requirements = ClaimRequirements.create(
                required_resolution_level=64.0,
                estimated_cost_units=100,
                required_observables=["camera", "imu"],
                method="sensor-fusion",
                regime_value=2.5,
            )
            result = runtime.qualify_claim(
                "out.of.profile",
                state_before={},
                state_after={},
                observation=SFOObservation(
                    source_id="camera-a",
                    source_class=SourceClass.OBSERVED.value,
                    value={"object": "vehicle"},
                    confidence=0.95,
                ),
                evidence=[EvidenceItem(1.0, 0.95, 0.95, 0.95)],
                profile=profile,
                requirements=requirements,
            )

            output = result["execution"]["output"]
            self.assertEqual(output["qualification"], "out_of_profile")
            self.assertEqual(output["profile"]["status"], "out_of_profile")
            self.assertEqual(len(output["profile"]["violations"]), 5)

    def test_reasoning_without_explicit_scope_holds_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, runtime = self._runtime(root)
            result = runtime.qualify_claim(
                "blocked.claim",
                state_before={},
                state_after={},
                observation=SFOObservation(
                    source_id="sensor-a",
                    source_class=SourceClass.OBSERVED.value,
                    value={"x": 1},
                    confidence=1.0,
                ),
                evidence=[EvidenceItem(1.0, 1.0, 1.0, 1.0)],
                profile=self._profile(),
                requirements=self._requirements(),
                consent_scope="unspecified",
            )

            self.assertEqual(result["authority"]["tre_logic"], "0")
            self.assertIsNone(result["execution"])
            self.assertEqual(result["receipt"]["source_class"], SourceClass.PROPOSED.value)
            self.assertTrue(result["chain"]["valid"])

    def test_provenance_aware_rag0shot_can_beat_similarity_only(self):
        trusted = RetrievalSignals(
            semantic=0.82,
            provenance=1.0,
            reliability=0.95,
            graph=0.80,
            temporal=0.90,
        )
        untrusted = RetrievalSignals(
            semantic=1.0,
            provenance=0.10,
            reliability=0.20,
            graph=0.30,
            temporal=0.90,
        )

        self.assertGreater(untrusted.semantic, trusted.semantic)
        self.assertGreater(rag0shot_score(trusted), rag0shot_score(untrusted))


if __name__ == "__main__":
    unittest.main()
