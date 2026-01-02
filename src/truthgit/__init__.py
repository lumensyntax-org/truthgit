"""
TruthGit - Version Control for Verified Truth

A distributed system where multiple validators (AI or human) can contribute,
verify, and reach consensus on verifiable claims.

> "Git is to code what TruthGit is to truth."

Quick Start:
    $ truthgit init
    $ truthgit claim "Water boils at 100°C at sea level" --domain physics
    $ truthgit verify
    ✓ Consensus: 94% (3/3 validators)

Knowledge Extraction:
    $ truthgit extract "document.txt" --domain physics
    $ truthgit patterns --domain physics
    $ truthgit axioms --promote
"""

from .extractor import (
    Contradiction,
    ContradictionSeverity,
    ExtractionResult,
    KnowledgeExtractor,
    Pattern,
    PatternType,
    extract_from_text,
)
from .hashing import content_hash, short_hash, verify_hash
from .objects import (
    Axiom,
    AxiomType,
    Claim,
    ClaimCategory,
    ClaimState,
    ConsensusResult,
    ConsensusType,
    Context,
    TruthObject,
    Verification,
    calculate_consensus,
)
from .repository import TruthRepository

__version__ = "0.2.0"
__author__ = "TruthGit"
__license__ = "MIT"

__all__ = [
    # Objects
    "Axiom",
    "AxiomType",
    "Claim",
    "ClaimCategory",
    "ClaimState",
    "Context",
    "Verification",
    "ConsensusResult",
    "ConsensusType",
    "TruthObject",
    # Functions
    "calculate_consensus",
    "content_hash",
    "verify_hash",
    "short_hash",
    # Repository
    "TruthRepository",
    # Extractor
    "KnowledgeExtractor",
    "Pattern",
    "PatternType",
    "Contradiction",
    "ContradictionSeverity",
    "ExtractionResult",
    "extract_from_text",
]
