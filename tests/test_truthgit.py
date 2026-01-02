"""Tests for TruthGit core functionality."""

import tempfile
from pathlib import Path

from truthgit import (
    Axiom,
    Claim,
    TruthRepository,
    calculate_consensus,
    content_hash,
    verify_hash,
)
from truthgit.objects import (
    AxiomType,
    ClaimCategory,
    ConsensusType,
    ObjectType,
)


class TestHashing:
    """Test content-addressable hashing."""

    def test_same_content_same_hash(self):
        content = {"type": "claim", "content": "Test"}
        assert content_hash(content) == content_hash(content)

    def test_different_content_different_hash(self):
        h1 = content_hash("content1")
        h2 = content_hash("content2")
        assert h1 != h2

    def test_key_order_doesnt_matter(self):
        h1 = content_hash({"b": 2, "a": 1})
        h2 = content_hash({"a": 1, "b": 2})
        assert h1 == h2

    def test_verify_hash(self):
        content = "test content"
        h = content_hash(content)
        assert verify_hash(content, h)
        assert not verify_hash("wrong content", h)


class TestObjects:
    """Test truth objects."""

    def test_claim_creation(self):
        claim = Claim(
            content="Python is dynamically typed",
            confidence=0.9,
            category=ClaimCategory.FACTUAL,
            domain="programming",
        )
        assert claim.object_type == ObjectType.CLAIM
        assert claim.confidence == 0.9
        assert len(claim.hash) == 64

    def test_axiom_confidence_is_one(self):
        axiom = Axiom(
            content="Speed of light is 299,792,458 m/s",
            axiom_type=AxiomType.SCIENTIFIC_CONSTANT,
            domain="physics",
            authority_source="BIPM",
        )
        assert axiom.confidence == 1.0
        assert axiom.object_type == ObjectType.AXIOM

    def test_serialization_roundtrip(self):
        claim = Claim(
            content="Test claim",
            confidence=0.8,
            category=ClaimCategory.FACTUAL,
            domain="test",
        )
        serialized = claim.serialize()
        from truthgit.objects import TruthObject

        deserialized = TruthObject.deserialize(serialized)
        assert deserialized.hash == claim.hash


class TestConsensus:
    """Test consensus calculation."""

    def test_majority_consensus(self):
        result = calculate_consensus(
            {
                "A": 0.8,
                "B": 0.7,
                "C": 0.75,
            }
        )
        assert result.passed
        assert result.consensus_type == ConsensusType.SUPERMAJORITY

    def test_failed_consensus(self):
        result = calculate_consensus(
            {
                "A": 0.3,
                "B": 0.4,
                "C": 0.5,
            }
        )
        assert not result.passed
        assert result.consensus_type == ConsensusType.DISPUTED

    def test_unanimous_consensus(self):
        result = calculate_consensus(
            {
                "A": 1.0,
                "B": 1.0,
                "C": 1.0,
            }
        )
        assert result.passed
        assert result.consensus_type == ConsensusType.UNANIMOUS


class TestRepository:
    """Test truth repository."""

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()
            assert repo.is_initialized()

    def test_claim_and_stage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            claim = repo.claim(
                content="Test claim",
                confidence=0.8,
                domain="test",
            )

            staged = repo.get_staged()
            assert len(staged) == 1
            assert staged[0]["hash"] == claim.hash

    def test_verify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            repo.claim(content="Test", confidence=0.8, domain="test")

            verification = repo.verify(
                verifier_results={
                    "A": (0.85, "Looks good"),
                    "B": (0.80, "Verified"),
                    "C": (0.82, "Confirmed"),
                }
            )

            assert verification is not None
            assert verification.consensus.passed

    def test_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            repo.claim(content="Claim 1", confidence=0.8, domain="test")
            repo.verify(verifier_results={"A": (0.9, "OK"), "B": (0.85, "OK")})

            repo.claim(content="Claim 2", confidence=0.8, domain="test")
            repo.verify(verifier_results={"A": (0.88, "OK"), "B": (0.82, "OK")})

            history = repo.history()
            assert len(history) == 2

    def test_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            status = repo.status()
            assert status["initialized"]
            assert status["staged_count"] == 0
