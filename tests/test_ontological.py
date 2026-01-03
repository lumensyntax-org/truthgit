"""
Tests for Ontological Classification system.

Tests the three-type disagreement taxonomy:
- LOGICAL_ERROR: Bug in validator
- MYSTERY: Legitimate unknowable
- GAP: Requires human mediation
"""

import pytest

from truthgit.fallacy_detector import detect_fallacies, FallacyCategory
from truthgit.hypothesis_tester import (
    evaluate_hypothesis,
    EpistemicStatus,
    HypothesisType,
)
from truthgit.ontological_classifier import (
    classify_disagreement,
    calculate_ontological_consensus,
    DisagreementType,
    ConsensusStatus,
)


# =============================================================================
# FALLACY DETECTION TESTS
# =============================================================================

class TestFallacyDetection:
    """Test fallacy detection functionality."""

    def test_ad_hominem_detection(self):
        """Should detect ad hominem attacks."""
        argument = "He's an idiot, so his argument is wrong."
        result = detect_fallacies(argument)

        assert not result.valid
        assert len(result.fallacies) >= 1
        assert any(f.type == "AD_HOMINEM" for f in result.fallacies)

    def test_false_dilemma_detection(self):
        """Should detect false dilemmas."""
        argument = "Either you're with us or against us."
        result = detect_fallacies(argument)

        assert not result.valid
        assert any(f.type == "FALSE_DILEMMA" for f in result.fallacies)

    def test_slippery_slope_detection(self):
        """Should detect slippery slope arguments."""
        argument = "If we allow this, then eventually we'll lose all our freedoms."
        result = detect_fallacies(argument)

        assert not result.valid
        assert any(f.type == "SLIPPERY_SLOPE" for f in result.fallacies)

    def test_valid_argument(self):
        """Should pass valid arguments."""
        argument = "The data shows a correlation of 0.85 between X and Y."
        result = detect_fallacies(argument)

        assert result.valid
        assert len(result.fallacies) == 0


# =============================================================================
# HYPOTHESIS TESTING TESTS
# =============================================================================

class TestHypothesisTester:
    """Test hypothesis evaluation functionality."""

    def test_unfalsifiable_claim(self):
        """Should identify unfalsifiable claims."""
        claim = "Everything happens for a reason."
        result = evaluate_hypothesis(claim)

        assert result.status == EpistemicStatus.UNFALSIFIABLE
        assert not result.falsifiable

    def test_fringe_claim(self):
        """Should identify fringe claims."""
        claim = "The Earth is flat."
        result = evaluate_hypothesis(claim)

        assert result.status == EpistemicStatus.FRINGE

    def test_contested_claim(self):
        """Should identify contested claims."""
        claim = "Free will exists."
        result = evaluate_hypothesis(claim)

        assert result.status == EpistemicStatus.CONTESTED

    def test_established_claim(self):
        """Should identify established science."""
        claim = "Evolution explains biodiversity."
        result = evaluate_hypothesis(claim)

        assert result.status == EpistemicStatus.ESTABLISHED

    def test_causal_hypothesis_type(self):
        """Should correctly classify causal hypotheses."""
        claim = "Smoking causes cancer."
        result = evaluate_hypothesis(claim)

        assert result.type == HypothesisType.CAUSAL

    def test_universal_hypothesis_type(self):
        """Should correctly classify universal hypotheses."""
        claim = "All swans are white."
        result = evaluate_hypothesis(claim)

        assert result.type == HypothesisType.UNIVERSAL


# =============================================================================
# DISAGREEMENT CLASSIFICATION TESTS
# =============================================================================

class TestDisagreementClassification:
    """Test ontological classification of disagreements."""

    def test_logical_error_from_fallacy(self):
        """Should classify as LOGICAL_ERROR when fallacy detected."""
        result = classify_disagreement(
            claim="Climate change is real",
            position_a="The data clearly shows warming trends.",
            position_b="He's a liar, so his climate data is wrong."  # Ad hominem
        )

        assert result.type == DisagreementType.LOGICAL_ERROR
        assert result.fallacy_count_b > 0

    def test_mystery_from_contested(self):
        """Should classify as MYSTERY for contested claims."""
        result = classify_disagreement(
            claim="Consciousness is fundamental to reality",
            domain="philosophy"
        )

        assert result.type == DisagreementType.MYSTERY
        assert result.claim_status == EpistemicStatus.CONTESTED

    def test_gap_from_unfalsifiable(self):
        """Should classify as GAP for unfalsifiable claims."""
        result = classify_disagreement(
            claim="Everything happens for a reason",
            domain="philosophy"
        )

        assert result.type == DisagreementType.GAP
        assert result.claim_status == EpistemicStatus.UNFALSIFIABLE


# =============================================================================
# ONTOLOGICAL CONSENSUS TESTS
# =============================================================================

class TestOntologicalConsensus:
    """Test the full ontological consensus calculation."""

    def test_high_agreement_passes(self):
        """High agreement should pass without ontological analysis."""
        results = {
            "CLAUDE": (0.92, "Scientifically accurate"),
            "GPT": (0.88, "Correct based on physics"),
            "GEMINI": (0.90, "Verified"),
        }

        consensus = calculate_ontological_consensus(
            claim="Water boils at 100°C at sea level",
            validator_results=results,
            threshold=0.66
        )

        assert consensus.status == ConsensusStatus.PASSED
        assert consensus.value > 0.85
        assert consensus.disagreement_type is None

    def test_logical_error_excludes_outlier(self):
        """Should exclude outlier on LOGICAL_ERROR."""
        results = {
            "CLAUDE": (0.95, "Scientifically accurate"),
            "GPT": (0.92, "Correct based on physics"),
            "BROKEN": (0.15, "He's an idiot so it's wrong"),  # Fallacy + outlier
        }

        consensus = calculate_ontological_consensus(
            claim="E=mc²",
            validator_results=results,
            threshold=0.66
        )

        assert consensus.status == ConsensusStatus.PASSED
        assert consensus.disagreement_type == DisagreementType.LOGICAL_ERROR
        assert "BROKEN" in (consensus.excluded_validators or [])
        assert consensus.value > 0.90  # Recalculated without outlier

    def test_mystery_preserves_positions(self):
        """MYSTERY should preserve all positions as data."""
        results = {
            "CLAUDE": (0.70, "Free will emerges from complexity"),
            "GPT": (0.30, "Determinism is more parsimonious"),
            "GEMINI": (0.50, "The question may be malformed"),
        }

        consensus = calculate_ontological_consensus(
            claim="Free will exists",
            validator_results=results,
            threshold=0.66,
            domain="philosophy"
        )

        assert consensus.status == ConsensusStatus.UNRESOLVABLE
        assert consensus.disagreement_type == DisagreementType.MYSTERY
        assert consensus.preserved_positions is not None
        assert len(consensus.preserved_positions) == 3

    def test_gap_triggers_mediation(self):
        """GAP should request human mediation."""
        results = {
            "CLAUDE": (0.80, "This is a matter of values"),
            "GPT": (0.20, "Cannot determine objectively"),
        }

        consensus = calculate_ontological_consensus(
            claim="Everything happens for a reason",
            validator_results=results,
            threshold=0.66,
            domain="philosophy"
        )

        assert consensus.status == ConsensusStatus.PENDING_MEDIATION
        assert consensus.disagreement_type == DisagreementType.GAP
        assert consensus.mediation_context is not None
        assert "Mediation Required" in consensus.mediation_context


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_physics_claim_high_consensus(self):
        """Physics claims with high consensus should pass cleanly."""
        results = {
            "OLLAMA:LLAMA3": (0.94, "Accurate under standard atmospheric pressure"),
            "OLLAMA:MISTRAL": (0.92, "True at 1 atm, varies with altitude"),
            "OLLAMA:PHI3": (0.95, "Correct for pure water at sea level"),
        }

        consensus = calculate_ontological_consensus(
            claim="Water boils at 100°C at sea level",
            validator_results=results,
            threshold=0.66,
            domain="physics"
        )

        assert consensus.passed
        assert consensus.value > 0.90

    def test_philosophy_claim_preserves_mystery(self):
        """Philosophy claims should often preserve as MYSTERY."""
        # Higher variance to trigger ontological analysis
        results = {
            "CLAUDE": (0.75, "Consciousness may be emergent"),
            "GPT": (0.25, "Hard problem remains unsolved"),
            "GEMINI": (0.50, "Depends on definition of consciousness"),
        }

        consensus = calculate_ontological_consensus(
            claim="Consciousness is fundamental",
            validator_results=results,
            threshold=0.66,
            domain="philosophy"
        )

        # Should NOT fail, should preserve as MYSTERY
        assert consensus.status == ConsensusStatus.UNRESOLVABLE
        assert consensus.preserved_positions is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
