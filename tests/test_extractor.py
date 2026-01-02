"""Tests for KnowledgeExtractor functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from truthgit import TruthRepository
from truthgit.extractor import (
    Contradiction,
    ContradictionSeverity,
    ExtractionResult,
    KnowledgeExtractor,
    Pattern,
    PatternType,
    extract_from_text,
)


class TestPattern:
    """Test Pattern dataclass."""

    def test_pattern_hash(self):
        p1 = Pattern(
            pattern_type=PatternType.CAUSAL,
            claims=["hash1", "hash2"],
            description="A causes B",
            confidence=0.8,
        )
        p2 = Pattern(
            pattern_type=PatternType.CAUSAL,
            claims=["hash1", "hash2"],
            description="A causes B",
            confidence=0.9,  # Different confidence
        )
        # Same type, claims, description = same hash
        assert p1.hash == p2.hash

    def test_pattern_different_claims(self):
        p1 = Pattern(
            pattern_type=PatternType.CAUSAL,
            claims=["hash1", "hash2"],
            description="A causes B",
            confidence=0.8,
        )
        p2 = Pattern(
            pattern_type=PatternType.CAUSAL,
            claims=["hash1", "hash3"],
            description="A causes B",
            confidence=0.8,
        )
        assert p1.hash != p2.hash


class TestContradiction:
    """Test Contradiction dataclass."""

    def test_contradiction_hash(self):
        c = Contradiction(
            claim_a_hash="hash1",
            claim_b_hash="hash2",
            severity=ContradictionSeverity.DIRECT,
            explanation="They contradict",
            confidence=0.9,
        )
        assert len(c.hash) == 64

    def test_contradiction_order_independent(self):
        c1 = Contradiction(
            claim_a_hash="hash1",
            claim_b_hash="hash2",
            severity=ContradictionSeverity.DIRECT,
            explanation="They contradict",
            confidence=0.9,
        )
        c2 = Contradiction(
            claim_a_hash="hash2",
            claim_b_hash="hash1",
            severity=ContradictionSeverity.DIRECT,
            explanation="They contradict",
            confidence=0.9,
        )
        # Note: In current implementation, these will have different hashes
        # A future improvement could normalize the order
        assert c1.hash != c2.hash  # Current behavior


class TestKnowledgeExtractor:
    """Test KnowledgeExtractor with mocked LLM."""

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            assert extractor.repo == repo
            assert extractor.use_local is True
            assert extractor.parser_model == "llama3"

    @patch.object(KnowledgeExtractor, "_call_llm")
    def test_ingest_document(self, mock_llm):
        """Test document ingestion with mocked LLM."""
        mock_llm.return_value = """[
            {"content": "Water boils at 100°C at sea level", "confidence": 0.95},
            {"content": "Ice melts at 0°C", "confidence": 0.95}
        ]"""

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            claims = extractor.ingest_document(
                document="Water boils at 100°C at sea level. Ice melts at 0°C.",
                domain="physics",
            )

            assert len(claims) == 2
            assert claims[0].content == "Water boils at 100°C at sea level"
            assert claims[1].content == "Ice melts at 0°C"
            assert claims[0].domain == "physics"

    @patch.object(KnowledgeExtractor, "_call_llm")
    def test_ingest_filters_low_confidence(self, mock_llm):
        """Test that low confidence claims are filtered."""
        mock_llm.return_value = """[
            {"content": "High confidence claim", "confidence": 0.9},
            {"content": "Low confidence claim", "confidence": 0.3}
        ]"""

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            claims = extractor.ingest_document(
                document="Test document",
                domain="test",
                min_confidence=0.5,
            )

            assert len(claims) == 1
            assert claims[0].content == "High confidence claim"

    @patch.object(KnowledgeExtractor, "_call_llm")
    def test_find_patterns(self, mock_llm):
        """Test pattern detection with mocked LLM."""
        # First call for ingestion
        mock_llm.side_effect = [
            """[
                {"content": "Claim A", "confidence": 0.9},
                {"content": "Claim B", "confidence": 0.9}
            ]""",
            # Second call for pattern detection
            """[
                {"type": "causal", "claim_indices": [0, 1],
                 "description": "A causes B", "confidence": 0.8}
            ]""",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            claims = extractor.ingest_document("Test doc", domain="test")
            patterns = extractor.find_patterns(claims)

            assert len(patterns) == 1
            assert patterns[0].pattern_type == PatternType.CAUSAL
            assert patterns[0].description == "A causes B"

    @patch.object(KnowledgeExtractor, "_call_llm")
    def test_detect_contradictions(self, mock_llm):
        """Test contradiction detection with mocked LLM."""
        # Setup: ingest two claims
        mock_llm.side_effect = [
            """[{"content": "Water boils at 100°C", "confidence": 0.9}]""",
            """[{"content": "Water boils at 50°C", "confidence": 0.9}]""",
            # Contradiction detection call
            """{
                "contradicts": true,
                "severity": "direct",
                "explanation": "Different boiling points",
                "confidence": 0.95,
                "resolution_hint": "Check pressure conditions"
            }""",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            claim1 = extractor.ingest_document("Water boils at 100°C", domain="physics")
            claim2 = extractor.ingest_document("Water boils at 50°C", domain="physics")

            contradictions = extractor.detect_contradictions(claim2[0], against=claim1)

            assert len(contradictions) == 1
            assert contradictions[0].severity == ContradictionSeverity.DIRECT
            assert "Different boiling points" in contradictions[0].explanation

    @patch.object(KnowledgeExtractor, "_call_llm")
    def test_detect_no_contradiction(self, mock_llm):
        """Test when claims don't contradict."""
        mock_llm.side_effect = [
            """[{"content": "Water boils at 100°C", "confidence": 0.9}]""",
            """[{"content": "Water is H2O", "confidence": 0.9}]""",
            """{
                "contradicts": false,
                "severity": "none",
                "explanation": "No contradiction",
                "confidence": 0.95
            }""",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            claim1 = extractor.ingest_document("Water boils at 100°C", domain="physics")
            claim2 = extractor.ingest_document("Water is H2O", domain="physics")

            contradictions = extractor.detect_contradictions(claim2[0], against=claim1)

            assert len(contradictions) == 0

    def test_find_axiom_candidates_no_verifications(self):
        """Test that claims without verifications are not candidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            # Create a claim but don't verify it
            repo.claim(content="Test claim", confidence=0.9, domain="test")

            extractor = KnowledgeExtractor(repo)
            candidates = extractor.find_axiom_candidates()

            assert len(candidates) == 0

    def test_extract_domain_graph_empty(self):
        """Test graph extraction with no claims."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            extractor = KnowledgeExtractor(repo)
            graph = extractor.extract_domain_graph("physics")

            assert graph["domain"] == "physics"
            assert graph["nodes"] == []
            assert graph["edges"] == []


class TestExtractionResult:
    """Test ExtractionResult dataclass."""

    def test_extraction_result_creation(self):
        result = ExtractionResult(
            source_hash="abc123",
            claims=[],
            patterns=[],
            contradictions=[],
        )
        assert result.source_hash == "abc123"
        assert result.claims == []
        assert result.patterns == []


class TestExtractFromText:
    """Test the convenience function."""

    @patch.object(KnowledgeExtractor, "_call_llm")
    def test_extract_from_text(self, mock_llm):
        mock_llm.return_value = """[
            {"content": "Test claim", "confidence": 0.9}
        ]"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result = extract_from_text(
                text="Test document",
                domain="test",
                repo_path=str(Path(tmpdir) / ".truth"),
            )

            assert isinstance(result, ExtractionResult)
            assert len(result.claims) == 1
