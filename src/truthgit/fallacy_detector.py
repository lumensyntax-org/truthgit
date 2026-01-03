"""
TruthGit - Fallacy Detector
Detects logical fallacies in arguments.

Ported from TruthSyntax TypeScript implementation.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class FallacyCategory(Enum):
    FORMAL = "FORMAL"
    INFORMAL = "INFORMAL"


@dataclass
class FallacyMatch:
    """A detected fallacy in an argument."""

    type: str
    confidence: float
    explanation: str
    category: FallacyCategory


@dataclass
class FallacyResult:
    """Result of fallacy detection analysis."""

    valid: bool
    fallacies: list[FallacyMatch]
    recommendation: str


# =============================================================================
# FORMAL FALLACIES - Errors in logical structure
# =============================================================================


def _check_affirming_consequent(text: str) -> bool:
    """If A then B. B. Therefore A."""
    lower = text.lower()
    has_conditional = bool(re.search(r"if\s+.+,?\s*(then)?\s+.+", lower, re.IGNORECASE))
    pattern = r"(therefore|so|thus|hence)\s+.*(did|was|is|happened)"
    affirms_then = bool(re.search(pattern, lower, re.IGNORECASE))
    return has_conditional and affirms_then


def _check_denying_antecedent(text: str) -> bool:
    """Concluding negation of consequent from negation of antecedent."""
    lower = text.lower()
    has_conditional = bool(re.search(r"if\s+.+,?\s*(then)?\s+.+", lower, re.IGNORECASE))
    pattern = r"(didn't|doesn't|not|never)\s+.*(therefore|so|thus)"
    denies_if = bool(re.search(pattern, lower, re.IGNORECASE))
    return has_conditional and denies_if


def _check_false_dilemma(text: str) -> bool:
    """Presenting only two options when more exist."""
    lower = text.lower()
    return bool(re.search(r"either\s+.+\s+or\s+", lower, re.IGNORECASE)) or bool(
        re.search(r"only\s+(two|2)\s+(options|choices|ways)", lower, re.IGNORECASE)
    )


def _check_circular_reasoning(text: str) -> bool:
    """The conclusion is assumed in one of the premises."""
    lower = text.lower()
    return bool(re.search(r"because.+because|true.+true|valid.+valid", lower, re.IGNORECASE))


FORMAL_FALLACIES: dict[str, tuple[Callable[[str], bool], str]] = {
    "AFFIRMING_CONSEQUENT": (
        _check_affirming_consequent,
        "Concluding the antecedent from the consequent (If A then B. B. Therefore A.)",
    ),
    "DENYING_ANTECEDENT": (
        _check_denying_antecedent,
        "Concluding negation of consequent from negation of antecedent",
    ),
    "FALSE_DILEMMA": (_check_false_dilemma, "Presenting only two options when more exist"),
    "CIRCULAR_REASONING": (
        _check_circular_reasoning,
        "The conclusion is assumed in one of the premises",
    ),
}


# =============================================================================
# INFORMAL FALLACIES - Errors in reasoning content
# =============================================================================


def _check_ad_hominem(text: str) -> bool:
    """Attacking the person instead of their argument."""
    lower = text.lower()
    # Pattern 1: "he's an idiot", "she is a liar", etc.
    pattern1 = re.search(
        r"(he|she|they|you|'s)\s*(is|are|'s|'re)?\s*(a\s+|an\s+)?(liar|idiot|fool|hypocrite|biased|stupid|wrong)",
        lower,
        re.IGNORECASE,
    )
    # Pattern 2: Direct insult like "he's an idiot"
    pattern2 = re.search(
        r"(idiot|liar|fool|stupid|hypocrite).*(so|therefore|hence)", lower, re.IGNORECASE
    )
    # Pattern 3: "don't trust/listen to X because..."
    pattern3 = re.search(
        r"don't\s+(listen|trust|believe)\s+(to|in)?\s*\w+\s+(because|since)", lower, re.IGNORECASE
    )
    return bool(pattern1 or pattern2 or pattern3)


def _check_straw_man(text: str) -> bool:
    """Misrepresenting someone's argument to make it easier to attack."""
    lower = text.lower()
    return bool(re.search(r"so\s+(you're|you are)\s+saying", lower, re.IGNORECASE)) or bool(
        re.search(r"what\s+(he|she|they)\s+(really|actually)\s+mean", lower, re.IGNORECASE)
    )


def _check_appeal_to_authority(text: str) -> bool:
    """Using authority as evidence instead of actual evidence."""
    lower = text.lower()
    pattern = r"(expert|scientist|doctor|study|research)\s+(says?|said|shows?|proved?)"
    return bool(re.search(pattern, lower, re.IGNORECASE))


def _check_slippery_slope(text: str) -> bool:
    """Assuming a chain of events without justification."""
    lower = text.lower()
    pat = r"(if|once)\s+we\s+.+,?\s+(then|next|soon|eventually)"
    pattern1 = re.search(pat, lower, re.IGNORECASE)
    pattern2 = re.search(r"will\s+lead\s+to", lower, re.IGNORECASE)
    return bool(pattern1 or pattern2)


def _check_hasty_generalization(text: str) -> bool:
    """Drawing broad conclusions from insufficient samples."""
    lower = text.lower()
    has_universal = bool(re.search(r"(all|every|always|never|none)\s", lower, re.IGNORECASE))
    sample_pat = r"(met|saw|know|heard of)\s+(one|a|two|few|some)"
    has_limited_sample = bool(re.search(sample_pat, lower, re.IGNORECASE))
    return has_universal and has_limited_sample


def _check_false_cause(text: str) -> bool:
    """Assuming causation from correlation (post hoc ergo propter hoc)."""
    lower = text.lower()
    pattern1 = re.search(r"after\s+.+,?\s*.+(happened|started|began|caused)", lower, re.IGNORECASE)
    pattern2 = re.search(r"ever\s+since\s+.+,?\s*.+therefore", lower, re.IGNORECASE)
    return bool(pattern1 or pattern2)


def _check_appeal_to_emotion(text: str) -> bool:
    """Using emotion instead of evidence."""
    lower = text.lower()
    pat1 = r"think\s+of\s+the\s+(children|victims|families)"
    pat2 = r"how\s+would\s+you\s+feel"
    return bool(re.search(pat1, lower, re.IGNORECASE)) or bool(
        re.search(pat2, lower, re.IGNORECASE)
    )


INFORMAL_FALLACIES: dict[str, tuple[Callable[[str], bool], str]] = {
    "AD_HOMINEM": (_check_ad_hominem, "Attacking the person instead of their argument"),
    "STRAW_MAN": (
        _check_straw_man,
        "Misrepresenting someone's argument to make it easier to attack",
    ),
    "APPEAL_TO_AUTHORITY": (
        _check_appeal_to_authority,
        "Using authority as evidence instead of actual evidence",
    ),
    "SLIPPERY_SLOPE": (_check_slippery_slope, "Assuming a chain of events without justification"),
    "HASTY_GENERALIZATION": (
        _check_hasty_generalization,
        "Drawing broad conclusions from insufficient samples",
    ),
    "FALSE_CAUSE": (
        _check_false_cause,
        "Assuming causation from correlation (post hoc ergo propter hoc)",
    ),
    "APPEAL_TO_EMOTION": (_check_appeal_to_emotion, "Using emotion instead of evidence"),
}


def detect_fallacies(argument: str, context: str | None = None) -> FallacyResult:
    """
    Detect logical fallacies in an argument.

    Args:
        argument: The argument text to analyze
        context: Optional additional context

    Returns:
        FallacyResult with detected fallacies and recommendation
    """
    fallacies: list[FallacyMatch] = []
    full_text = f"{context} {argument}" if context else argument

    # Check formal fallacies
    for name, (check_fn, description) in FORMAL_FALLACIES.items():
        if check_fn(full_text):
            fallacies.append(
                FallacyMatch(
                    type=name,
                    confidence=0.85,
                    explanation=description,
                    category=FallacyCategory.FORMAL,
                )
            )

    # Check informal fallacies
    for name, (check_fn, description) in INFORMAL_FALLACIES.items():
        if check_fn(full_text):
            fallacies.append(
                FallacyMatch(
                    type=name,
                    confidence=0.80,
                    explanation=description,
                    category=FallacyCategory.INFORMAL,
                )
            )

    # Generate recommendation
    if len(fallacies) == 0:
        recommendation = "No logical fallacies detected. Verify factual claims separately."
    elif len(fallacies) == 1:
        fallacy_name = fallacies[0].type.replace("_", " ").lower()
        recommendation = f"Consider restructuring to avoid {fallacy_name}."
    else:
        recommendation = (
            f"Multiple fallacies detected ({len(fallacies)}). The argument requires restructuring."
        )

    return FallacyResult(
        valid=len(fallacies) == 0, fallacies=fallacies, recommendation=recommendation
    )
