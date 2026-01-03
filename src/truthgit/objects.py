"""
TruthGit Objects - Los 4 tipos de objetos fundamentales

Axiom      → Verdad inmutable (constantes, definiciones)
Claim      → Afirmación verificable
Context    → Árbol de claims relacionados
Verification → Snapshot de verdad verificada (commit)
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .hashing import content_hash

# === Enums ===


class ObjectType(str, Enum):
    AXIOM = "axiom"
    CLAIM = "claim"
    CONTEXT = "context"
    VERIFICATION = "verification"


class AxiomType(str, Enum):
    SCIENTIFIC_CONSTANT = "scientific_constant"
    MATHEMATICAL_DEFINITION = "mathematical_definition"
    LOGICAL_TAUTOLOGY = "logical_tautology"
    LINGUISTIC_DEFINITION = "linguistic_definition"


class ClaimCategory(str, Enum):
    FACTUAL = "factual"
    INTERPRETIVE = "interpretive"
    PREDICTIVE = "predictive"
    DEFINITIONAL = "definitional"
    CAUSAL = "causal"


class ClaimState(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    VERIFIED = "verified"
    CONSENSUS = "consensus"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class RelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    REQUIRES = "requires"
    DERIVES = "derives"
    EXEMPLIFIES = "exemplifies"


class ConsensusType(str, Enum):
    UNANIMOUS = "unanimous"  # 100% acuerdo
    SUPERMAJORITY = "supermajority"  # >= 75%
    MAJORITY = "majority"  # >= 66%
    DISPUTED = "disputed"  # < 66%


# === Base Class ===


class TruthObject(ABC):
    """Clase base para todos los objetos de TruthGit."""

    @property
    @abstractmethod
    def object_type(self) -> ObjectType:
        """Tipo de objeto."""
        pass

    @abstractmethod
    def to_canonical(self) -> dict[str, Any]:
        """Convertir a diccionario canónico para hashing."""
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario completo para serialización."""
        pass

    @property
    def hash(self) -> str:
        """Hash SHA-256 del contenido canónico."""
        return content_hash(self.to_canonical(), prefix=self.object_type.value)

    @property
    def short_hash(self) -> str:
        """Hash corto (8 caracteres) para display."""
        return self.hash[:8]

    def serialize(self) -> str:
        """Serializar para almacenamiento."""
        data = self.to_dict()
        data["$type"] = self.object_type.value
        data["$hash"] = self.hash
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def deserialize(cls, data: str) -> "TruthObject":
        """Deserializar desde almacenamiento."""
        obj = json.loads(data)
        obj_type = obj.pop("$type")
        stored_hash = obj.pop("$hash", None)

        # Factory para crear el tipo correcto
        if obj_type == ObjectType.AXIOM.value:
            instance = Axiom.from_dict(obj)
        elif obj_type == ObjectType.CLAIM.value:
            instance = Claim.from_dict(obj)
        elif obj_type == ObjectType.CONTEXT.value:
            instance = Context.from_dict(obj)
        elif obj_type == ObjectType.VERIFICATION.value:
            instance = Verification.from_dict(obj)
        else:
            raise ValueError(f"Unknown object type: {obj_type}")

        # Verificar integridad
        if stored_hash and instance.hash != stored_hash:
            raise ValueError(
                f"Hash mismatch: stored {stored_hash[:8]}, computed {instance.short_hash}"
            )

        return instance


# === AXIOM ===


@dataclass
class Axiom(TruthObject):
    """
    Verdad inmutable que no requiere verificación externa.
    Confianza = 1.0 por definición.

    Ejemplos:
    - Constantes físicas (velocidad de la luz)
    - Definiciones matemáticas (π)
    - Tautologías lógicas (A = A)
    """

    content: str
    axiom_type: AxiomType
    domain: str
    authority_source: str
    authority_reference: str = ""
    established_date: str = ""
    language: str = "es"
    aliases: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "SYSTEM"

    @property
    def object_type(self) -> ObjectType:
        return ObjectType.AXIOM

    @property
    def confidence(self) -> float:
        return 1.0  # Axiomas siempre tienen confianza 1.0

    def to_canonical(self) -> dict[str, Any]:
        return {
            "type": "axiom",
            "content": self.content,
            "axiom_type": self.axiom_type.value,
            "domain": self.domain,
            "authority_source": self.authority_source,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "axiom_type": self.axiom_type.value,
            "domain": self.domain,
            "authority": {
                "source": self.authority_source,
                "reference": self.authority_reference,
                "established": self.established_date,
            },
            "metadata": {
                "language": self.language,
                "aliases": self.aliases,
                "created_at": self.created_at,
                "created_by": self.created_by,
            },
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Axiom":
        authority = data.get("authority", {})
        metadata = data.get("metadata", {})
        return cls(
            content=data["content"],
            axiom_type=AxiomType(data["axiom_type"]),
            domain=data["domain"],
            authority_source=authority.get("source", ""),
            authority_reference=authority.get("reference", ""),
            established_date=authority.get("established", ""),
            language=metadata.get("language", "es"),
            aliases=metadata.get("aliases", []),
            created_at=metadata.get("created_at", datetime.now().isoformat()),
            created_by=metadata.get("created_by", "SYSTEM"),
        )


# === CLAIM ===


@dataclass
class Source:
    """Fuente que soporta un claim."""

    url: str
    title: str = ""
    source_type: str = "PRIMARY"  # PRIMARY, SECONDARY, TERTIARY
    accessed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reliability: float = 0.8


@dataclass
class VerifierRecord:
    """Registro de verificación por un agente."""

    verifier: str  # e.g., "CLAUDE.ANALYST"
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Claim(TruthObject):
    """
    Afirmación verificable con nivel de confianza variable.

    Puede ser verificada por múltiples agentes y tener versiones.
    """

    content: str
    confidence: float
    category: ClaimCategory
    domain: str
    sources: list[Source] = field(default_factory=list)
    verified_by: list[VerifierRecord] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)  # hashes
    contradicts: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    supersedes: str | None = None  # hash of previous version
    state: ClaimState = ClaimState.DRAFT
    language: str = "es"
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""

    @property
    def object_type(self) -> ObjectType:
        return ObjectType.CLAIM

    def to_canonical(self) -> dict[str, Any]:
        return {
            "type": "claim",
            "content": self.content,
            "domain": self.domain,
            "sources": sorted([s.url for s in self.sources]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "confidence": self.confidence,
            "category": self.category.value,
            "domain": self.domain,
            "sources": [
                {
                    "url": s.url,
                    "title": s.title,
                    "type": s.source_type,
                    "accessed_at": s.accessed_at,
                    "reliability": s.reliability,
                }
                for s in self.sources
            ],
            "verified_by": [
                {
                    "verifier": v.verifier,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                    "timestamp": v.timestamp,
                }
                for v in self.verified_by
            ],
            "relations": {
                "supports": self.supports,
                "contradicts": self.contradicts,
                "requires": self.requires,
                "supersedes": self.supersedes,
            },
            "state": self.state.value,
            "metadata": {
                "language": self.language,
                "tags": self.tags,
                "created_at": self.created_at,
                "created_by": self.created_by,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Claim":
        sources = [
            Source(
                url=s["url"],
                title=s.get("title", ""),
                source_type=s.get("type", "PRIMARY"),
                accessed_at=s.get("accessed_at", ""),
                reliability=s.get("reliability", 0.8),
            )
            for s in data.get("sources", [])
        ]

        verified_by = [
            VerifierRecord(
                verifier=v["verifier"],
                confidence=v["confidence"],
                reasoning=v.get("reasoning", ""),
                timestamp=v.get("timestamp", ""),
            )
            for v in data.get("verified_by", [])
        ]

        relations = data.get("relations", {})
        metadata = data.get("metadata", {})

        return cls(
            content=data["content"],
            confidence=data["confidence"],
            category=ClaimCategory(data["category"]),
            domain=data["domain"],
            sources=sources,
            verified_by=verified_by,
            supports=relations.get("supports", []),
            contradicts=relations.get("contradicts", []),
            requires=relations.get("requires", []),
            supersedes=relations.get("supersedes"),
            state=ClaimState(data.get("state", "draft")),
            language=metadata.get("language", "es"),
            tags=metadata.get("tags", []),
            created_at=metadata.get("created_at", ""),
            created_by=metadata.get("created_by", ""),
        )

    def add_verification(self, verifier: str, confidence: float, reasoning: str):
        """Agregar verificación de un agente."""
        self.verified_by.append(
            VerifierRecord(
                verifier=verifier,
                confidence=confidence,
                reasoning=reasoning,
            )
        )
        # Actualizar confianza como promedio ponderado
        if self.verified_by:
            self.confidence = sum(v.confidence for v in self.verified_by) / len(self.verified_by)
            self.state = ClaimState.VERIFIED


# === CONTEXT ===


@dataclass
class ClaimRef:
    """Referencia a un claim dentro de un context."""

    hash: str
    role: str = "PRIMARY"  # PRIMARY, SUPPORTING, DERIVED


@dataclass
class ContextRef:
    """Referencia a un subcontexto."""

    hash: str
    relation: str = "CONTAINS"  # CONTAINS, SPECIALIZES, EXTENDS


@dataclass
class Relation:
    """Relación entre dos claims."""

    from_hash: str
    to_hash: str
    relation_type: RelationType


@dataclass
class Context(TruthObject):
    """
    Árbol/grafo de claims y axioms relacionados.
    Similar a Tree en Git.
    """

    name: str
    domain: str
    description: str = ""
    axioms: list[str] = field(default_factory=list)  # hashes
    claims: list[ClaimRef] = field(default_factory=list)
    subcontexts: list[ContextRef] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""

    @property
    def object_type(self) -> ObjectType:
        return ObjectType.CONTEXT

    def to_canonical(self) -> dict[str, Any]:
        return {
            "type": "context",
            "domain": self.domain,
            "axioms": sorted(self.axioms),
            "claims": sorted([c.hash for c in self.claims]),
            "subcontexts": sorted([s.hash for s in self.subcontexts]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "axioms": self.axioms,
            "claims": [{"hash": c.hash, "role": c.role} for c in self.claims],
            "subcontexts": [{"hash": s.hash, "relation": s.relation} for s in self.subcontexts],
            "relations": [
                {
                    "from": r.from_hash,
                    "to": r.to_hash,
                    "type": r.relation_type.value,
                }
                for r in self.relations
            ],
            "metadata": {
                "created_at": self.created_at,
                "created_by": self.created_by,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Context":
        claims = [
            ClaimRef(hash=c["hash"], role=c.get("role", "PRIMARY")) for c in data.get("claims", [])
        ]
        subcontexts = [
            ContextRef(hash=s["hash"], relation=s.get("relation", "CONTAINS"))
            for s in data.get("subcontexts", [])
        ]
        relations = [
            Relation(
                from_hash=r["from"],
                to_hash=r["to"],
                relation_type=RelationType(r["type"]),
            )
            for r in data.get("relations", [])
        ]
        metadata = data.get("metadata", {})

        return cls(
            name=data["name"],
            domain=data["domain"],
            description=data.get("description", ""),
            axioms=data.get("axioms", []),
            claims=claims,
            subcontexts=subcontexts,
            relations=relations,
            created_at=metadata.get("created_at", ""),
            created_by=metadata.get("created_by", ""),
        )


# === VERIFICATION ===


@dataclass
class VerifierVote:
    """Voto de un verificador en una verification."""

    roles: list[str]
    confidence: float
    reasoning: str
    claims_reviewed: int = 0
    claims_approved: int = 0
    claims_disputed: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConsensusResult:
    """Resultado del cálculo de consenso."""

    consensus_type: ConsensusType
    value: float
    threshold: float
    passed: bool
    weights: dict[str, float] = field(default_factory=dict)


@dataclass
class Verification(TruthObject):
    """
    Snapshot de verdad verificada - equivale a Commit en Git.

    Contiene:
    - Referencia al context verificado
    - Parent (verification anterior)
    - Votos de cada verificador
    - Resultado del consenso
    - Ontological consensus (v0.5.0+): understands NATURE of disagreement
    """

    context_hash: str
    parent_hash: str | None
    verifiers: dict[str, VerifierVote]
    consensus: ConsensusResult
    trigger: str = "manual"  # manual, scheduled, pr_review
    session_id: str = ""
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # v0.5.0: Ontological consensus (optional for backward compat during transition)
    ontological_consensus: Any | None = None  # OntologicalConsensus from ontological_classifier

    @property
    def object_type(self) -> ObjectType:
        return ObjectType.VERIFICATION

    def to_canonical(self) -> dict[str, Any]:
        return {
            "type": "verification",
            "context": self.context_hash,
            "parent": self.parent_hash,
            "verifiers": {k: v.confidence for k, v in sorted(self.verifiers.items())},
            "timestamp": self.timestamp,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context_hash,
            "parent": self.parent_hash,
            "verifiers": {
                k: {
                    "roles": v.roles,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                    "claims_reviewed": v.claims_reviewed,
                    "claims_approved": v.claims_approved,
                    "claims_disputed": v.claims_disputed,
                    "timestamp": v.timestamp,
                }
                for k, v in self.verifiers.items()
            },
            "consensus": {
                "type": self.consensus.consensus_type.value,
                "value": self.consensus.value,
                "threshold": self.consensus.threshold,
                "passed": self.consensus.passed,
                "weights": self.consensus.weights,
            },
            "metadata": {
                "trigger": self.trigger,
                "session_id": self.session_id,
                "duration_ms": self.duration_ms,
                "timestamp": self.timestamp,
            },
            # v0.5.0: Ontological consensus
            "ontological_consensus": (
                self._serialize_ontological() if self.ontological_consensus else None
            ),
        }

    def _serialize_ontological(self) -> dict | None:
        """Serialize ontological consensus to dict."""
        if not self.ontological_consensus:
            return None
        oc = self.ontological_consensus
        return {
            "status": oc.status.value if hasattr(oc.status, "value") else str(oc.status),
            "value": oc.value,
            "threshold": oc.threshold,
            "disagreement_type": oc.disagreement_type.value if oc.disagreement_type else None,
            "preserved_positions": oc.preserved_positions,
            "mediation_context": oc.mediation_context,
            "excluded_validators": oc.excluded_validators,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Verification":
        verifiers = {
            k: VerifierVote(
                roles=v.get("roles", []),
                confidence=v["confidence"],
                reasoning=v.get("reasoning", ""),
                claims_reviewed=v.get("claims_reviewed", 0),
                claims_approved=v.get("claims_approved", 0),
                claims_disputed=v.get("claims_disputed", 0),
                timestamp=v.get("timestamp", ""),
            )
            for k, v in data.get("verifiers", {}).items()
        }

        consensus_data = data.get("consensus", {})
        consensus = ConsensusResult(
            consensus_type=ConsensusType(consensus_data.get("type", "disputed")),
            value=consensus_data.get("value", 0),
            threshold=consensus_data.get("threshold", 0.66),
            passed=consensus_data.get("passed", False),
            weights=consensus_data.get("weights", {}),
        )

        metadata = data.get("metadata", {})

        # v0.5.0: Deserialize ontological consensus if present
        ontological = None
        oc_data = data.get("ontological_consensus")
        if oc_data:
            from .ontological_classifier import (
                ConsensusStatus,
                DisagreementType,
                OntologicalConsensus,
            )

            ontological = OntologicalConsensus(
                status=ConsensusStatus(oc_data["status"]),
                value=oc_data["value"],
                threshold=oc_data["threshold"],
                disagreement_type=(
                    DisagreementType(oc_data["disagreement_type"])
                    if oc_data.get("disagreement_type")
                    else None
                ),
                preserved_positions=oc_data.get("preserved_positions"),
                mediation_context=oc_data.get("mediation_context"),
                excluded_validators=oc_data.get("excluded_validators"),
            )

        return cls(
            context_hash=data["context"],
            parent_hash=data.get("parent"),
            verifiers=verifiers,
            consensus=consensus,
            trigger=metadata.get("trigger", "manual"),
            session_id=metadata.get("session_id", ""),
            duration_ms=metadata.get("duration_ms", 0),
            timestamp=metadata.get("timestamp", ""),
            ontological_consensus=ontological,
        )


# === Factory Functions ===


def calculate_consensus(
    verifier_confidences: dict[str, float],
    threshold: float = 0.66,
    weights: dict[str, float] | None = None,
) -> ConsensusResult:
    """
    Calcular consenso a partir de confidencias de verificadores.

    Args:
        verifier_confidences: {"CLAUDE": 0.85, "GPT": 0.78, ...}
        threshold: Umbral para considerar consenso alcanzado
        weights: Pesos por verificador (default: iguales)

    Returns:
        ConsensusResult con tipo, valor y si pasó el umbral
    """
    if not verifier_confidences:
        return ConsensusResult(
            consensus_type=ConsensusType.DISPUTED,
            value=0,
            threshold=threshold,
            passed=False,
        )

    # Pesos por defecto: iguales
    if weights is None:
        n = len(verifier_confidences)
        weights = {k: 1.0 / n for k in verifier_confidences}

    # Promedio ponderado
    value = sum(verifier_confidences[k] * weights.get(k, 0) for k in verifier_confidences)

    # Determinar tipo de consenso
    if value >= 1.0:
        consensus_type = ConsensusType.UNANIMOUS
    elif value >= 0.75:
        consensus_type = ConsensusType.SUPERMAJORITY
    elif value >= threshold:
        consensus_type = ConsensusType.MAJORITY
    else:
        consensus_type = ConsensusType.DISPUTED

    return ConsensusResult(
        consensus_type=consensus_type,
        value=value,
        threshold=threshold,
        passed=value >= threshold,
        weights=weights,
    )


# === Tests ===


def _test_objects():
    """Pruebas de los objetos."""

    # Test Axiom
    axiom = Axiom(
        content="La velocidad de la luz es 299,792,458 m/s",
        axiom_type=AxiomType.SCIENTIFIC_CONSTANT,
        domain="physics.constants",
        authority_source="BIPM",
    )
    assert axiom.confidence == 1.0
    assert axiom.object_type == ObjectType.AXIOM
    print(f"✅ Axiom: {axiom.short_hash}")

    # Test Claim
    claim = Claim(
        content="GPT-4 fue lanzado en marzo 2023",
        confidence=0.95,
        category=ClaimCategory.FACTUAL,
        domain="ai.models",
        sources=[Source(url="https://openai.com/blog/gpt-4", title="OpenAI Blog")],
    )
    claim.add_verification("CLAUDE.ANALYST", 0.92, "Verificado contra fuente primaria")
    assert claim.state == ClaimState.VERIFIED
    print(f"✅ Claim: {claim.short_hash}")

    # Test Context
    context = Context(
        name="AI Releases 2023",
        domain="ai.models.2023",
        claims=[ClaimRef(hash=claim.hash, role="PRIMARY")],
        axioms=[axiom.hash],
    )
    print(f"✅ Context: {context.short_hash}")

    # Test Verification
    consensus = calculate_consensus({"CLAUDE": 0.85, "GPT": 0.78, "GRAVITY": 0.82})
    verification = Verification(
        context_hash=context.hash,
        parent_hash=None,
        verifiers={
            "CLAUDE": VerifierVote(roles=["ANALYST"], confidence=0.85, reasoning="OK"),
            "GPT": VerifierVote(roles=["ANALYST"], confidence=0.78, reasoning="OK"),
            "GRAVITY": VerifierVote(roles=["SYNTHESIZER"], confidence=0.82, reasoning="OK"),
        },
        consensus=consensus,
    )
    assert verification.consensus.passed
    print(f"✅ Verification: {verification.short_hash}")

    # Test serialization roundtrip
    serialized = axiom.serialize()
    deserialized = TruthObject.deserialize(serialized)
    assert deserialized.hash == axiom.hash
    print("✅ Serialization roundtrip works")

    print("\n✅ All object tests passed")


if __name__ == "__main__":
    _test_objects()
