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
"""

from .objects import (
    Axiom,
    AxiomType,
    Claim,
    ClaimCategory,
    ClaimState,
    Context,
    Verification,
    ConsensusResult,
    ConsensusType,
    TruthObject,
    calculate_consensus,
)
from .hashing import content_hash, verify_hash, short_hash
from .repository import TruthRepository

__version__ = "0.1.0"
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
]
