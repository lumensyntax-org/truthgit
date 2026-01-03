"""
TruthGit - Hypothesis Tester
Evaluates hypotheses for falsifiability and scientific rigor.

Ported from TruthSyntax TypeScript implementation.
"""

import re
from dataclasses import dataclass
from enum import Enum


class HypothesisType(Enum):
    EMPIRICAL = "EMPIRICAL"
    THEORETICAL = "THEORETICAL"
    STATISTICAL = "STATISTICAL"
    CAUSAL = "CAUSAL"
    EXISTENTIAL = "EXISTENTIAL"
    UNIVERSAL = "UNIVERSAL"


class EpistemicStatus(Enum):
    ESTABLISHED = "ESTABLISHED"  # Scientific consensus
    CONTESTED = "CONTESTED"  # Active debate, legitimate positions
    SPECULATIVE = "SPECULATIVE"  # Testable but untested
    FRINGE = "FRINGE"  # Contradicts consensus
    UNFALSIFIABLE = "UNFALSIFIABLE"  # Cannot be tested


@dataclass
class HypothesisResult:
    """Result of hypothesis evaluation."""

    hypothesis: str
    type: HypothesisType
    status: EpistemicStatus
    falsifiable: bool
    falsifiability_score: float
    falsification_criteria: list[str]
    testable_experiments: list[str]
    recommendation: str


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

UNFALSIFIABLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"everything happens for a reason", re.IGNORECASE), "Tautological"),
    (
        re.compile(r"too subtle to (measure|detect)", re.IGNORECASE),
        "Conveniently immune to measurement",
    ),
    (
        re.compile(r"beyond (science|measurement)", re.IGNORECASE),
        "Defined outside empirical reach",
    ),
    (
        re.compile(r"you (just |have to )?(believe|have faith)", re.IGNORECASE),
        "Appeals to faith",
    ),
    (
        re.compile(r"works? in mysterious ways", re.IGNORECASE),
        "Explanatory black box",
    ),
    (
        re.compile(r"quantum.*(consciousness|healing|manifestation)", re.IGNORECASE),
        "Misuse of quantum mechanics",
    ),
]

FRINGE_KEYWORDS = [
    "flat earth",
    "earth is flat",
    "perpetual motion",
    "astrology",
    "homeopathy",
    "crystal healing",
    "psychic",
    "chemtrails",
    "lizard people",
    "anti-vax",
    "moon landing fake",
]

ESTABLISHED_KEYWORDS = [
    "photosynthesis",
    "evolution",
    "gravity",
    "thermodynamics",
    "germ theory",
    "dna",
    "relativity",
    "electromagnetic",
]

CONTESTED_KEYWORDS = [
    "dark matter",
    "dark energy",
    "consciousness",
    "free will",
    "multiverse",
    "string theory",
    "panpsychism",
    "qualia",
]


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================


def classify_type(hypothesis: str) -> HypothesisType:
    """Classify the type of hypothesis based on its structure."""
    lower = hypothesis.lower()

    if re.search(r"(all|every|always|never)", lower, re.IGNORECASE):
        return HypothesisType.UNIVERSAL
    if re.search(r"(causes?|leads? to|results? in)", lower, re.IGNORECASE):
        return HypothesisType.CAUSAL
    if re.search(r"(\d+%|percent|probability|correlation)", lower, re.IGNORECASE):
        return HypothesisType.STATISTICAL
    if re.search(r"(exists?|there (is|are))", lower, re.IGNORECASE):
        return HypothesisType.EXISTENTIAL
    if re.search(r"(theory|model|predicts?)", lower, re.IGNORECASE):
        return HypothesisType.THEORETICAL

    return HypothesisType.EMPIRICAL


def classify_status(hypothesis: str) -> EpistemicStatus:
    """Classify the epistemic status of a hypothesis."""
    lower = hypothesis.lower()

    # Check for fringe claims first
    if any(kw in lower for kw in FRINGE_KEYWORDS):
        return EpistemicStatus.FRINGE

    # Check for unfalsifiable patterns
    if any(pattern.search(lower) for pattern, _ in UNFALSIFIABLE_PATTERNS):
        return EpistemicStatus.UNFALSIFIABLE

    # Check for established science
    if any(kw in lower for kw in ESTABLISHED_KEYWORDS):
        return EpistemicStatus.ESTABLISHED

    # Check for contested topics
    if any(kw in lower for kw in CONTESTED_KEYWORDS):
        return EpistemicStatus.CONTESTED

    return EpistemicStatus.SPECULATIVE


def evaluate_falsifiability(hypothesis: str) -> tuple[bool, float, list[str]]:
    """
    Evaluate how falsifiable a hypothesis is.

    Returns:
        Tuple of (is_falsifiable, score, falsification_criteria)
    """
    lower = hypothesis.lower()
    score = 1.0
    criteria: list[str] = []
    matched_unfalsifiable = False

    # Check for unfalsifiable patterns
    for pattern, reason in UNFALSIFIABLE_PATTERNS:
        if pattern.search(lower):
            score -= 0.3
            matched_unfalsifiable = True

    # If we matched an unfalsifiable pattern, it's NOT falsifiable
    # regardless of the score
    if matched_unfalsifiable:
        return (False, max(0.0, score), ["Cannot be empirically tested"])

    # Generate falsification criteria based on type
    hyp_type = classify_type(hypothesis)

    if hyp_type == HypothesisType.UNIVERSAL:
        criteria.append("A single counterexample would refute this claim")
    elif hyp_type == HypothesisType.CAUSAL:
        criteria.append("Controlled experiment showing no effect")
        criteria.append("Alternative causal mechanism")
    elif hyp_type == HypothesisType.STATISTICAL:
        criteria.append("Larger study showing no correlation")
        criteria.append("Identification of confounding variables")
    else:
        criteria.append("Direct measurement contradicting the claim")
        criteria.append("Replication failure under same conditions")

    return (score > 0.5, max(0.0, score), criteria)


def generate_experiments(hyp_type: HypothesisType) -> list[str]:
    """Generate suggested experiments based on hypothesis type."""
    experiments = {
        HypothesisType.CAUSAL: [
            "Randomized controlled trial",
            "Natural experiment",
            "Time-series analysis",
        ],
        HypothesisType.STATISTICAL: [
            "Large-scale observational study",
            "Meta-analysis",
            "Prospective cohort study",
        ],
        HypothesisType.UNIVERSAL: ["Systematic search for counterexamples", "Edge case testing"],
        HypothesisType.EXISTENTIAL: ["Targeted search", "Improved detection methods"],
    }

    return experiments.get(hyp_type, ["Direct measurement", "Independent replication"])


def evaluate_hypothesis(
    hypothesis: str, domain: str | None = None, context: str | None = None
) -> HypothesisResult:
    """
    Evaluate a hypothesis for falsifiability and scientific rigor.

    Args:
        hypothesis: The hypothesis to evaluate
        domain: Optional scientific domain
        context: Optional additional context

    Returns:
        HypothesisResult with complete evaluation
    """
    hyp_type = classify_type(hypothesis)
    status = classify_status(hypothesis)
    falsifiable, score, criteria = evaluate_falsifiability(hypothesis)
    experiments = generate_experiments(hyp_type)

    # Generate recommendation based on status
    if status == EpistemicStatus.UNFALSIFIABLE:
        recommendation = (
            "Cannot be scientifically tested. Reformulate to make specific predictions."
        )
    elif status == EpistemicStatus.FRINGE:
        recommendation = (
            "Contradicts scientific consensus. Extraordinary claims require extraordinary evidence."
        )
    elif not falsifiable:
        recommendation = "Has falsifiability issues. Specify what evidence would disprove it."
    elif status == EpistemicStatus.SPECULATIVE:
        recommendation = "Testable and consistent. Proceed with experimental design."
    elif status == EpistemicStatus.CONTESTED:
        recommendation = "Active area of debate. Review current literature first."
    else:
        recommendation = "Aligns with established science. Consider novel predictions."

    return HypothesisResult(
        hypothesis=hypothesis,
        type=hyp_type,
        status=status,
        falsifiable=falsifiable,
        falsifiability_score=score,
        falsification_criteria=criteria,
        testable_experiments=experiments,
        recommendation=recommendation,
    )
