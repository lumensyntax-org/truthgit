"""
TruthGit - Ontological Classifier
Classifies the nature of disagreement rather than just counting votes.

The key insight: not all disagreement is equal.
- LOGICAL_ERROR: One validator has a bug or misunderstood
- MYSTERY: Legitimate disagreement about the unknowable
- GAP: Requires human mediation (values, interpretation)

This is the philosophical core that makes TruthGit different from
simple voting systems.
"""

import statistics
from dataclasses import dataclass, field
from enum import Enum

from .fallacy_detector import detect_fallacies
from .hypothesis_tester import EpistemicStatus, evaluate_hypothesis


class DisagreementType(Enum):
    """The ontological nature of a disagreement."""

    LOGICAL_ERROR = "logical_error"
    """One or more validators made an error (parsing, logic, hallucination).
    Action: Exclude outlier, recalculate consensus."""

    MYSTERY = "mystery"
    """Legitimate disagreement about something unknowable or contested.
    Action: Preserve all positions as valuable data."""

    GAP = "gap"
    """Disagreement stems from values, interpretation, or unfalsifiable claims.
    Action: Escalate to human mediation."""


class ConsensusStatus(Enum):
    """The result status of ontological consensus."""

    PASSED = "passed"
    """Consensus achieved after ontological analysis."""

    FAILED = "failed"
    """Consensus not achieved, claim rejected."""

    UNRESOLVABLE = "unresolvable"
    """MYSTERY detected - disagreement is preserved as information."""

    PENDING_MEDIATION = "pending_mediation"
    """GAP detected - requires human decision."""


@dataclass
class OntologicalConsensus:
    """
    Consensus that understands the NATURE of disagreement.

    Unlike simple voting (threshold-based), this preserves information
    about WHY validators disagreed.
    """

    status: ConsensusStatus
    value: float
    threshold: float
    disagreement_type: DisagreementType | None = None

    # For MYSTERY: preserve positions as valuable data
    preserved_positions: dict[str, str] | None = None

    # For GAP: information for human mediator
    mediation_context: str | None = None

    # For LOGICAL_ERROR: which validators were excluded
    excluded_validators: list[str] | None = None

    # Original validator results
    validator_details: dict[str, tuple[float, str]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Whether consensus was achieved (for backwards compatibility)."""
        return self.status == ConsensusStatus.PASSED


@dataclass
class DisagreementAnalysis:
    """Detailed analysis of a disagreement."""

    type: DisagreementType
    explanation: str
    claim_status: EpistemicStatus | None = None
    fallacy_count_a: int = 0
    fallacy_count_b: int = 0


def classify_disagreement(
    claim: str,
    position_a: str | None = None,
    position_b: str | None = None,
    domain: str | None = None,
) -> DisagreementAnalysis:
    """
    Classify the ontological nature of a disagreement.

    This is the core function that asks "WHAT type of disagreement?"
    instead of "HOW MUCH disagreement?"

    Args:
        claim: The disputed claim
        position_a: First validator's reasoning (optional)
        position_b: Second validator's reasoning (optional)
        domain: Knowledge domain (physics, philosophy, etc.)

    Returns:
        DisagreementAnalysis with classification and explanation
    """
    # Analyze the claim for falsifiability
    hypothesis_result = evaluate_hypothesis(claim, domain=domain)

    # Check for fallacies in positions if provided
    fallacies_a = detect_fallacies(position_a) if position_a else None
    fallacies_b = detect_fallacies(position_b) if position_b else None

    fallacy_count_a = len(fallacies_a.fallacies) if fallacies_a else 0
    fallacy_count_b = len(fallacies_b.fallacies) if fallacies_b else 0

    # Classification logic
    if fallacy_count_a > 0 or fallacy_count_b > 0:
        return DisagreementAnalysis(
            type=DisagreementType.LOGICAL_ERROR,
            explanation="One or both positions contain logical fallacies",
            claim_status=hypothesis_result.status,
            fallacy_count_a=fallacy_count_a,
            fallacy_count_b=fallacy_count_b,
        )

    if hypothesis_result.status == EpistemicStatus.UNFALSIFIABLE:
        return DisagreementAnalysis(
            type=DisagreementType.GAP,
            explanation=(
                "The claim is unfalsifiable - disagreement stems from values/interpretation"
            ),
            claim_status=hypothesis_result.status,
        )

    if hypothesis_result.status in (EpistemicStatus.CONTESTED, EpistemicStatus.SPECULATIVE):
        return DisagreementAnalysis(
            type=DisagreementType.MYSTERY,
            explanation=(
                "Insufficient evidence to resolve - legitimate positions exist on both sides"
            ),
            claim_status=hypothesis_result.status,
        )

    # Default: likely one position contradicts evidence
    return DisagreementAnalysis(
        type=DisagreementType.LOGICAL_ERROR,
        explanation="One position likely contradicts established evidence",
        claim_status=hypothesis_result.status,
    )


def identify_outlier(validator_results: dict[str, tuple[float, str]]) -> str | None:
    """
    Identify the statistical outlier among validators.

    Uses a simple approach: the validator furthest from the median.
    """
    if len(validator_results) < 3:
        return None

    confidences = {k: v[0] for k, v in validator_results.items()}
    median = statistics.median(confidences.values())

    max_deviation = 0.0
    outlier = None

    for validator, confidence in confidences.items():
        deviation = abs(confidence - median)
        if deviation > max_deviation:
            max_deviation = deviation
            outlier = validator

    # Only return outlier if deviation is significant (> 0.3)
    return outlier if max_deviation > 0.3 else None


def generate_mediation_brief(claim: str, validator_results: dict[str, tuple[float, str]]) -> str:
    """Generate a brief for human mediators."""
    lines = [
        "## Mediation Required",
        "",
        f"**Claim:** {claim}",
        "",
        "**Validator Positions:**",
    ]

    for validator, (confidence, reasoning) in validator_results.items():
        lines.append(f"- **{validator}** ({confidence:.0%}): {reasoning[:200]}...")

    lines.extend(
        [
            "",
            "**Why Mediation?**",
            "This disagreement cannot be resolved algorithmically because it involves",
            "unfalsifiable claims or value-based interpretations.",
            "",
            "**Action Required:** Human judgment on which position to accept.",
        ]
    )

    return "\n".join(lines)


def calculate_ontological_consensus(
    claim: str,
    validator_results: dict[str, tuple[float, str]],
    threshold: float = 0.66,
    domain: str | None = None,
) -> OntologicalConsensus:
    """
    Calculate consensus that understands the NATURE of the claim.

    This is the main entry point for ontological consensus.
    It asks "WHAT type of CLAIM?" FIRST, then "HOW MUCH agreement?"

    The key insight: the claim's epistemic nature determines handling,
    not validator variance. A contested claim with high agreement is
    still a MYSTERY - validators agreeing on uncertainty doesn't
    resolve the underlying unknowability.

    Flow:
    1. UNFALSIFIABLE claims → always GAP (requires human mediation)
    2. CONTESTED/SPECULATIVE claims → always MYSTERY (preserve as data)
    3. ESTABLISHED/FRINGE claims → use variance + threshold logic

    Args:
        claim: The claim being verified
        validator_results: Dict mapping validator name to (confidence, reasoning)
        threshold: Consensus threshold (default 0.66)
        domain: Knowledge domain for classification

    Returns:
        OntologicalConsensus with full analysis
    """
    if not validator_results:
        return OntologicalConsensus(
            status=ConsensusStatus.FAILED,
            value=0.0,
            threshold=threshold,
            disagreement_type=None,
            validator_details={},
        )

    confidences = [r[0] for r in validator_results.values()]
    reasonings = {k: r[1] for k, r in validator_results.items()}
    mean_confidence = statistics.mean(confidences)

    # Domains where claim nature takes precedence over validator agreement
    philosophical_domains = {"philosophy", "ethics", "religion", "metaphysics", "epistemology"}

    # For philosophical domains, analyze claim nature FIRST
    # The key insight: in philosophy, validators agreeing on uncertainty
    # doesn't resolve the underlying unknowability
    if domain and domain.lower() in philosophical_domains:
        hypothesis_result = evaluate_hypothesis(claim, domain=domain)

        # UNFALSIFIABLE claims → always GAP (requires human mediation)
        if hypothesis_result.status == EpistemicStatus.UNFALSIFIABLE:
            return OntologicalConsensus(
                status=ConsensusStatus.PENDING_MEDIATION,
                value=mean_confidence,
                threshold=threshold,
                disagreement_type=DisagreementType.GAP,
                mediation_context=generate_mediation_brief(claim, validator_results),
                validator_details=validator_results,
            )

        # CONTESTED/SPECULATIVE claims → always MYSTERY (preserve as data)
        if hypothesis_result.status in (EpistemicStatus.CONTESTED, EpistemicStatus.SPECULATIVE):
            return OntologicalConsensus(
                status=ConsensusStatus.UNRESOLVABLE,
                value=mean_confidence,
                threshold=threshold,
                disagreement_type=DisagreementType.MYSTERY,
                preserved_positions=reasonings,
                validator_details=validator_results,
            )

    # For non-philosophical domains or non-contested claims, use variance-based logic
    # High agreement on established claims → PASSED/FAILED
    # High variance suggests one validator erred → classify further

    if len(confidences) > 1:
        variance = statistics.variance(confidences)
    else:
        variance = 0.0

    # Low variance on falsifiable claims → simple threshold
    if variance < 0.02:
        status = ConsensusStatus.PASSED if mean_confidence >= threshold else ConsensusStatus.FAILED
        return OntologicalConsensus(
            status=status,
            value=mean_confidence,
            threshold=threshold,
            disagreement_type=None,
            validator_details=validator_results,
        )

    # HIGH VARIANCE on falsifiable claim → likely LOGICAL_ERROR
    # Get positions for fallacy analysis
    sorted_validators = sorted(validator_results.items(), key=lambda x: x[1][0])
    lowest = sorted_validators[0]
    highest = sorted_validators[-1]

    analysis = classify_disagreement(
        claim=claim,
        position_a=highest[1][1],  # Highest confidence reasoning
        position_b=lowest[1][1],  # Lowest confidence reasoning
        domain=domain,
    )

    # Handle based on disagreement type
    if analysis.type == DisagreementType.LOGICAL_ERROR:
        # Identify and exclude the outlier
        outlier = identify_outlier(validator_results)

        if outlier:
            filtered = {k: v for k, v in validator_results.items() if k != outlier}
            recalculated = statistics.mean([v[0] for v in filtered.values()])
            status = ConsensusStatus.PASSED if recalculated >= threshold else ConsensusStatus.FAILED

            return OntologicalConsensus(
                status=status,
                value=recalculated,
                threshold=threshold,
                disagreement_type=DisagreementType.LOGICAL_ERROR,
                excluded_validators=[outlier],
                validator_details=validator_results,
            )
        else:
            # No clear outlier, fail consensus
            return OntologicalConsensus(
                status=ConsensusStatus.FAILED,
                value=mean_confidence,
                threshold=threshold,
                disagreement_type=DisagreementType.LOGICAL_ERROR,
                validator_details=validator_results,
            )

    elif analysis.type == DisagreementType.MYSTERY:
        # PRESERVE the disagreement as valuable information
        return OntologicalConsensus(
            status=ConsensusStatus.UNRESOLVABLE,
            value=mean_confidence,
            threshold=threshold,
            disagreement_type=DisagreementType.MYSTERY,
            preserved_positions=reasonings,  # THIS IS THE VALUE
            validator_details=validator_results,
        )

    elif analysis.type == DisagreementType.GAP:
        # Escalate to human
        return OntologicalConsensus(
            status=ConsensusStatus.PENDING_MEDIATION,
            value=mean_confidence,
            threshold=threshold,
            disagreement_type=DisagreementType.GAP,
            mediation_context=generate_mediation_brief(claim, validator_results),
            validator_details=validator_results,
        )

    # Fallback (should not reach here)
    return OntologicalConsensus(
        status=ConsensusStatus.FAILED,
        value=mean_confidence,
        threshold=threshold,
        disagreement_type=None,
        validator_details=validator_results,
    )
