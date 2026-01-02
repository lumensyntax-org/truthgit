"""
TruthGit Knowledge Extractor - Extract verified knowledge from dense documents.

This module enables:
1. Parsing documents into atomic, verifiable claims
2. Finding patterns across verified claims
3. Detecting contradictions between claims
4. Promoting high-consensus claims to axioms

Usage:
    from truthgit import TruthRepository
    from truthgit.extractor import KnowledgeExtractor

    repo = TruthRepository(".truth")
    extractor = KnowledgeExtractor(repo)

    # Ingest a document
    claims = extractor.ingest_document(
        "Water boils at 100°C at sea level. Ice melts at 0°C.",
        domain="physics"
    )

    # Find patterns
    patterns = extractor.find_patterns()

    # Detect contradictions
    contradictions = extractor.detect_contradictions(new_claim)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from .hashing import content_hash
from .objects import Axiom, AxiomType, Claim, ClaimCategory, ObjectType

if TYPE_CHECKING:
    from .repository import TruthRepository


class PatternType(Enum):
    """Types of patterns that can be detected."""

    CAUSAL = "causal"  # A causes B
    TEMPORAL = "temporal"  # A happens before B
    HIERARCHICAL = "hierarchical"  # A is a type of B
    CORRELATIONAL = "correlational"  # A correlates with B
    DEFINITIONAL = "definitional"  # A is defined as B
    CONTRADICTORY = "contradictory"  # A contradicts B
    SUPPORTING = "supporting"  # A supports/confirms B
    DOMAIN_CLUSTER = "domain_cluster"  # Claims clustered by domain


class ContradictionSeverity(Enum):
    """How severe is a contradiction."""

    DIRECT = "direct"  # Explicit logical contradiction
    IMPLICIT = "implicit"  # Implied contradiction
    PARTIAL = "partial"  # Contradicts in some contexts
    POTENTIAL = "potential"  # Might contradict under interpretation


@dataclass
class Pattern:
    """A detected pattern between claims."""

    pattern_type: PatternType
    claims: list[str]  # List of claim hashes
    description: str
    confidence: float
    metadata: dict = field(default_factory=dict)
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def hash(self) -> str:
        return content_hash(
            {
                "type": self.pattern_type.value,
                "claims": sorted(self.claims),
                "description": self.description,
            }
        )


@dataclass
class Contradiction:
    """A detected contradiction between claims."""

    claim_a_hash: str
    claim_b_hash: str
    severity: ContradictionSeverity
    explanation: str
    confidence: float
    resolution_hint: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def hash(self) -> str:
        return content_hash(
            {
                "claim_a": self.claim_a_hash,
                "claim_b": self.claim_b_hash,
                "severity": self.severity.value,
            }
        )


@dataclass
class ExtractionResult:
    """Result of document extraction."""

    source_hash: str
    claims: list[Claim]
    patterns: list[Pattern]
    contradictions: list[Contradiction]
    metadata: dict = field(default_factory=dict)
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())


class KnowledgeExtractor:
    """
    Extract verified knowledge from documents.

    This class orchestrates the extraction pipeline:
    1. Document → Atomic Claims (using LLM)
    2. Claims → Patterns (semantic analysis)
    3. Claims → Contradictions (logical analysis)
    4. Claims → Axioms (consensus promotion)
    """

    PARSE_PROMPT = """\
You are a knowledge extraction system. Parse the following document into atomic, verifiable claims.

Rules:
1. Each claim must be a single, independent statement
2. Each claim must be verifiable (can be true or false)
3. Remove opinions, keep only factual statements
4. Preserve the original meaning precisely
5. Include domain-specific terminology

Document:
{document}

Domain: {domain}

Respond with a JSON array of claims:
[
    {{"content": "claim text", "confidence": 0.0-1.0, "category": "factual"}},
    ...
]

Valid categories: factual, definitional, causal, temporal

Only output valid JSON, no other text."""

    PATTERN_PROMPT = """\
Analyze these verified claims and identify patterns between them.

Claims:
{claims}

Identify patterns such as:
- Causal relationships (A causes B)
- Temporal sequences (A happens before B)
- Hierarchical relations (A is a type of B)
- Correlations (A correlates with B)
- Supporting evidence (A confirms B)

Respond with JSON:
[
    {{
        "type": "causal|temporal|hierarchical|correlational|supporting",
        "claim_indices": [0, 1],
        "description": "explanation",
        "confidence": 0.0-1.0
    }},
    ...
]

Only output valid JSON."""

    CONTRADICTION_PROMPT = """\
Analyze if these two claims contradict each other.

Claim A: {claim_a}
Claim B: {claim_b}

Consider:
1. Direct logical contradiction
2. Implicit contradiction
3. Partial contradiction (in some contexts)
4. No contradiction

Respond with JSON:
{{
    "contradicts": true|false,
    "severity": "direct|implicit|partial|none",
    "explanation": "why they contradict or don't",
    "confidence": 0.0-1.0,
    "resolution_hint": "how to resolve if contradictory"
}}

Only output valid JSON."""

    def __init__(
        self,
        repository: TruthRepository,
        parser_model: str = "llama3",
        use_local: bool = True,
    ):
        """
        Initialize the knowledge extractor.

        Args:
            repository: TruthGit repository for storage
            parser_model: Model to use for parsing (Ollama model name)
            use_local: Use local Ollama instead of cloud APIs
        """
        self.repo = repository
        self.parser_model = parser_model
        self.use_local = use_local
        self._extraction_cache: dict[str, ExtractionResult] = {}

    def _call_llm(self, prompt: str) -> str:
        """Call LLM for extraction tasks."""
        if self.use_local:
            return self._call_ollama(prompt)
        else:
            return self._call_cloud(prompt)

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama for local inference."""
        try:
            import httpx

            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.parser_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "{}")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}") from e

    def _call_cloud(self, prompt: str) -> str:
        """Call cloud API (Claude) for inference."""
        import os

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Cloud API error: {e}") from e

    def ingest_document(
        self,
        document: str,
        domain: str = "general",
        auto_verify: bool = False,
        min_confidence: float = 0.5,
    ) -> list[Claim]:
        """
        Parse a document into atomic, verifiable claims.

        Args:
            document: The text document to parse
            domain: Knowledge domain (physics, history, etc.)
            auto_verify: Automatically run verification on claims
            min_confidence: Minimum confidence to include claim

        Returns:
            List of Claim objects (staged in repository)
        """
        # Check cache
        doc_hash = content_hash({"document": document, "domain": domain})
        if doc_hash in self._extraction_cache:
            return self._extraction_cache[doc_hash].claims

        # Call LLM to parse document
        prompt = self.PARSE_PROMPT.format(document=document, domain=domain)
        response = self._call_llm(prompt)

        # Parse response
        try:
            parsed = json.loads(response)
            # Handle wrapped response {"claims": [...]}
            if isinstance(parsed, dict):
                if "claims" in parsed:
                    parsed = parsed["claims"]
                else:
                    parsed = [parsed]
            if not isinstance(parsed, list):
                parsed = [parsed]
        except json.JSONDecodeError:
            # Try to extract JSON array from response
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                # Try to extract JSON object
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    obj = json.loads(match.group())
                    parsed = obj.get("claims", [obj])
                else:
                    raise ValueError(f"Could not parse LLM response: {response[:200]}")

        # Create claims
        claims = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            content = item.get("content", "")
            if not content:
                continue

            confidence = float(item.get("confidence", 0.5))
            if confidence < min_confidence:
                continue

            category_str = item.get("category", "factual")
            try:
                category = ClaimCategory(category_str)
            except ValueError:
                category = ClaimCategory.FACTUAL

            # Create and stage claim
            claim = self.repo.claim(
                content=content,
                confidence=confidence,
                domain=domain,
                category=category.value,
            )
            claims.append(claim)

        # Auto-verify if requested
        if auto_verify and claims:
            from .validators import get_default_validators, validate_claim

            validators = get_default_validators(local_only=self.use_local)
            if len(validators) >= 2:
                for claim in claims:
                    results, avg = validate_claim(
                        claim=claim.content,
                        domain=domain,
                        validators=validators,
                    )
                    # Store results for later verification
                    claim.metadata = claim.metadata or {}
                    claim.metadata["validation_results"] = [
                        {"validator": r.validator_name, "confidence": r.confidence}
                        for r in results
                        if r.success
                    ]

        # Cache result
        self._extraction_cache[doc_hash] = ExtractionResult(
            source_hash=doc_hash,
            claims=claims,
            patterns=[],
            contradictions=[],
            metadata={"domain": domain, "document_length": len(document)},
        )

        return claims

    def find_patterns(
        self,
        claims: list[Claim] | None = None,
        domain: str | None = None,
        min_confidence: float = 0.6,
    ) -> list[Pattern]:
        """
        Find patterns across verified claims.

        Args:
            claims: Specific claims to analyze (default: all verified)
            domain: Filter by domain
            min_confidence: Minimum pattern confidence

        Returns:
            List of detected patterns
        """
        # Get claims to analyze
        if claims is None:
            claims = list(self.repo.iter_objects(ObjectType.CLAIM))
            if domain:
                claims = [c for c in claims if c.domain == domain]

        if len(claims) < 2:
            return []

        # Format claims for LLM
        claims_text = "\n".join(
            f"[{i}] {c.content} (confidence: {c.confidence:.0%})" for i, c in enumerate(claims)
        )

        # Call LLM for pattern detection
        prompt = self.PATTERN_PROMPT.format(claims=claims_text)
        response = self._call_llm(prompt)

        # Parse response
        try:
            parsed = json.loads(response)
            if not isinstance(parsed, list):
                parsed = [parsed]
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                return []

        # Create patterns
        patterns = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            confidence = float(item.get("confidence", 0.5))
            if confidence < min_confidence:
                continue

            try:
                pattern_type = PatternType(item.get("type", "correlational"))
            except ValueError:
                pattern_type = PatternType.CORRELATIONAL

            indices = item.get("claim_indices", [])
            if not indices or len(indices) < 2:
                continue

            # Map indices to claim hashes
            claim_hashes = []
            for idx in indices:
                if 0 <= idx < len(claims):
                    claim_hashes.append(claims[idx].hash)

            if len(claim_hashes) < 2:
                continue

            pattern = Pattern(
                pattern_type=pattern_type,
                claims=claim_hashes,
                description=item.get("description", ""),
                confidence=confidence,
            )
            patterns.append(pattern)

        return patterns

    def detect_contradictions(
        self,
        claim: Claim | str,
        against: list[Claim] | None = None,
        min_confidence: float = 0.7,
    ) -> list[Contradiction]:
        """
        Detect contradictions between a claim and existing verified claims.

        Args:
            claim: The claim to check (Claim object or content string)
            against: Claims to check against (default: all verified)
            min_confidence: Minimum contradiction confidence

        Returns:
            List of detected contradictions
        """
        # Normalize claim
        if isinstance(claim, str):
            claim_content = claim
            claim_hash = content_hash({"content": claim})
        else:
            claim_content = claim.content
            claim_hash = claim.hash

        # Get claims to check against
        if against is None:
            against = list(self.repo.iter_objects(ObjectType.CLAIM))

        contradictions = []
        for other in against:
            if other.hash == claim_hash:
                continue

            # Check for contradiction
            prompt = self.CONTRADICTION_PROMPT.format(
                claim_a=claim_content,
                claim_b=other.content,
            )
            response = self._call_llm(prompt)

            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                else:
                    continue

            if not parsed.get("contradicts", False):
                continue

            confidence = float(parsed.get("confidence", 0.5))
            if confidence < min_confidence:
                continue

            try:
                severity = ContradictionSeverity(parsed.get("severity", "potential"))
            except ValueError:
                severity = ContradictionSeverity.POTENTIAL

            contradiction = Contradiction(
                claim_a_hash=claim_hash,
                claim_b_hash=other.hash,
                severity=severity,
                explanation=parsed.get("explanation", ""),
                confidence=confidence,
                resolution_hint=parsed.get("resolution_hint", ""),
            )
            contradictions.append(contradiction)

        return contradictions

    def promote_to_axiom(
        self,
        claim: Claim,
        min_verifications: int = 3,
        min_avg_confidence: float = 0.95,
        authority_source: str = "TruthGit Consensus",
    ) -> Axiom | None:
        """
        Promote a claim to axiom status based on verification history.

        A claim can be promoted to axiom if:
        1. It has been verified multiple times
        2. Average confidence across verifications is very high
        3. No contradictions exist

        Args:
            claim: The claim to potentially promote
            min_verifications: Minimum number of verifications required
            min_avg_confidence: Minimum average confidence required
            authority_source: Source to cite for the axiom

        Returns:
            Axiom if promoted, None otherwise
        """
        # Check for contradictions
        contradictions = self.detect_contradictions(claim)
        if contradictions:
            return None

        # Get verification history for this claim
        verifications = []
        for v in self.repo.iter_objects(ObjectType.VERIFICATION):
            # Check if this verification includes our claim
            context = self.repo.load(ObjectType.CONTEXT, v.context_hash)
            if context:
                claim_hashes = [cr.hash for cr in context.claims]
                if claim.hash in claim_hashes:
                    verifications.append(v)

        if len(verifications) < min_verifications:
            return None

        # Calculate average confidence across verifications
        total_confidence = 0.0
        count = 0
        for v in verifications:
            if v.consensus.passed:
                total_confidence += v.consensus.value
                count += 1

        if count == 0:
            return None

        avg_confidence = total_confidence / count
        if avg_confidence < min_avg_confidence:
            return None

        # Create axiom
        axiom = Axiom(
            content=claim.content,
            axiom_type=AxiomType.VERIFIED_FACT,
            domain=claim.domain,
            authority_source=authority_source,
            authority_reference=f"Promoted from claim {claim.short_hash} "
            f"with {count} verifications at {avg_confidence:.1%} avg confidence",
        )

        # Store axiom
        self.repo.store(axiom)

        return axiom

    def find_axiom_candidates(
        self,
        min_verifications: int = 2,
        min_avg_confidence: float = 0.90,
    ) -> list[tuple[Claim, float, int]]:
        """
        Find claims that are candidates for axiom promotion.

        Returns:
            List of (claim, avg_confidence, verification_count) tuples
        """
        candidates = []

        for claim in self.repo.iter_objects(ObjectType.CLAIM):
            # Get verifications
            verifications = []
            for v in self.repo.iter_objects(ObjectType.VERIFICATION):
                context = self.repo.load(ObjectType.CONTEXT, v.context_hash)
                if context:
                    claim_hashes = [cr.hash for cr in context.claims]
                    if claim.hash in claim_hashes and v.consensus.passed:
                        verifications.append(v)

            if len(verifications) < min_verifications:
                continue

            avg_confidence = sum(v.consensus.value for v in verifications) / len(verifications)
            if avg_confidence >= min_avg_confidence:
                candidates.append((claim, avg_confidence, len(verifications)))

        # Sort by confidence descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def extract_domain_graph(self, domain: str) -> dict:
        """
        Extract a knowledge graph for a specific domain.

        Returns a graph structure with:
        - nodes: claims and axioms
        - edges: patterns and relationships

        Args:
            domain: The domain to extract

        Returns:
            Dict with 'nodes' and 'edges'
        """
        nodes = []
        edges = []

        # Get all claims in domain
        claims = [c for c in self.repo.iter_objects(ObjectType.CLAIM) if c.domain == domain]

        # Get all axioms in domain
        axioms = [a for a in self.repo.iter_objects(ObjectType.AXIOM) if a.domain == domain]

        # Add nodes
        for claim in claims:
            nodes.append(
                {
                    "id": claim.hash,
                    "type": "claim",
                    "content": claim.content,
                    "confidence": claim.confidence,
                    "short_hash": claim.short_hash,
                }
            )

        for axiom in axioms:
            nodes.append(
                {
                    "id": axiom.hash,
                    "type": "axiom",
                    "content": axiom.content,
                    "confidence": 1.0,
                    "short_hash": axiom.short_hash,
                }
            )

        # Find patterns (edges)
        if claims:
            patterns = self.find_patterns(claims, domain=domain)
            for pattern in patterns:
                if len(pattern.claims) >= 2:
                    for i in range(len(pattern.claims) - 1):
                        edges.append(
                            {
                                "source": pattern.claims[i],
                                "target": pattern.claims[i + 1],
                                "type": pattern.pattern_type.value,
                                "description": pattern.description,
                                "confidence": pattern.confidence,
                            }
                        )

        return {
            "domain": domain,
            "nodes": nodes,
            "edges": edges,
            "extracted_at": datetime.now().isoformat(),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def extract_from_text(
    text: str,
    domain: str = "general",
    repo_path: str = ".truth",
    auto_verify: bool = False,
) -> ExtractionResult:
    """
    Convenience function to extract knowledge from text.

    Args:
        text: The text to extract from
        domain: Knowledge domain
        repo_path: Path to truth repository
        auto_verify: Run verification automatically

    Returns:
        ExtractionResult with claims, patterns, and contradictions
    """
    from .repository import TruthRepository

    repo = TruthRepository(repo_path)
    if not repo.is_initialized():
        repo.init()

    extractor = KnowledgeExtractor(repo)
    claims = extractor.ingest_document(text, domain=domain, auto_verify=auto_verify)
    patterns = extractor.find_patterns(claims, domain=domain)

    # Check for contradictions among extracted claims
    contradictions = []
    for claim in claims:
        for c in extractor.detect_contradictions(claim, against=claims):
            if c not in contradictions:
                contradictions.append(c)

    return ExtractionResult(
        source_hash=content_hash({"text": text}),
        claims=claims,
        patterns=patterns,
        contradictions=contradictions,
        metadata={"domain": domain, "text_length": len(text)},
    )
