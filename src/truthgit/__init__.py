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

# Ontological Classification (v0.5.0)
from .fallacy_detector import (
    FallacyCategory,
    FallacyMatch,
    FallacyResult,
    detect_fallacies,
)
from .hashing import content_hash, short_hash, verify_hash
from .hypothesis_tester import (
    EpistemicStatus,
    HypothesisResult,
    HypothesisType,
    evaluate_hypothesis,
)
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
from .ontological_classifier import (
    ConsensusStatus,
    DisagreementAnalysis,
    DisagreementType,
    OntologicalConsensus,
    calculate_ontological_consensus,
    classify_disagreement,
)
from .proof import (
    ProofCertificate,
    ProofManager,
    verify_proof_standalone,
)
from .repository import TruthRepository
from .sync import (
    DocumentSync,
    SyncedFile,
    SyncResult,
    SyncState,
    sync_docs,
)
from .validators import (
    ClaudeValidator,
    GeminiValidator,
    GPTValidator,
    HuggingFaceValidator,
    HumanValidator,
    Logos6Validator,
    OllamaValidator,
    ValidationResult,
    Validator,
    get_default_validators,
    validate_claim,
)

__version__ = "0.5.1"
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
    # Sync
    "DocumentSync",
    "SyncedFile",
    "SyncResult",
    "SyncState",
    "sync_docs",
    # Validators
    "Validator",
    "ValidationResult",
    "OllamaValidator",
    "ClaudeValidator",
    "GPTValidator",
    "GeminiValidator",
    "HuggingFaceValidator",
    "Logos6Validator",
    "HumanValidator",
    "get_default_validators",
    "validate_claim",
    # Proof
    "ProofCertificate",
    "ProofManager",
    "verify_proof_standalone",
    # Ontological Classification
    "DisagreementType",
    "ConsensusStatus",
    "OntologicalConsensus",
    "DisagreementAnalysis",
    "classify_disagreement",
    "calculate_ontological_consensus",
    # Fallacy Detection
    "FallacyCategory",
    "FallacyMatch",
    "FallacyResult",
    "detect_fallacies",
    # Hypothesis Testing
    "HypothesisType",
    "EpistemicStatus",
    "HypothesisResult",
    "evaluate_hypothesis",
]
