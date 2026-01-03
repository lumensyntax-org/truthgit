"""
TruthGit Repository - El .truth/ directory

Similar a .git/, almacena todos los objetos y referencias.
"""

import json
import shutil
import zlib
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from .hashing import hash_to_path, path_to_hash
from .objects import (
    Axiom,
    Claim,
    ClaimRef,
    Context,
    ObjectType,
    TruthObject,
    Verification,
    VerifierVote,
    calculate_consensus,
)

T = TypeVar("T", bound=TruthObject)


class TruthRepository:
    """
    Repositorio de verdad - equivalente a un Git repository.

    Estructura:
    .truth/
    ├── objects/          # Base de datos de objetos
    │   ├── ax/           # Axioms
    │   ├── cl/           # Claims
    │   ├── ct/           # Contexts
    │   └── vf/           # Verifications
    ├── refs/             # Referencias
    │   ├── perspectives/ # Por verificador
    │   ├── consensus/    # Verdad consensuada
    │   └── anchors/      # Referencias fijas
    ├── HEAD              # Perspectiva actual
    ├── index             # Staging area
    └── config            # Configuración
    """

    OBJECT_PREFIXES = {
        ObjectType.AXIOM: "ax",
        ObjectType.CLAIM: "cl",
        ObjectType.CONTEXT: "ct",
        ObjectType.VERIFICATION: "vf",
    }

    def __init__(self, path: str = ".truth"):
        self.root = Path(path)
        self.objects_dir = self.root / "objects"
        self.refs_dir = self.root / "refs"
        self.head_file = self.root / "HEAD"
        self.index_file = self.root / "index"
        self.config_file = self.root / "config"

    # === Initialization ===

    def init(self, force: bool = False) -> bool:
        """
        Inicializar un nuevo repositorio de verdad.

        Similar a `git init`.
        """
        if self.root.exists():
            if not force:
                raise FileExistsError(f"Repository already exists at {self.root}")
            shutil.rmtree(self.root)

        # Crear estructura de directorios
        for prefix in self.OBJECT_PREFIXES.values():
            (self.objects_dir / prefix).mkdir(parents=True)

        (self.refs_dir / "perspectives").mkdir(parents=True)
        (self.refs_dir / "consensus").mkdir(parents=True)
        (self.refs_dir / "anchors").mkdir(parents=True)

        # Crear HEAD (apunta a consensus/main por defecto)
        self.head_file.write_text("ref: consensus/main\n")

        # Crear index vacío
        self._write_index({"staged": [], "timestamp": datetime.now().isoformat()})

        # Crear config
        config = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "consensus_threshold": 0.66,
            "default_verifiers": ["CLAUDE", "GPT", "GRAVITY"],
        }
        self.config_file.write_text(json.dumps(config, indent=2))

        # Generate proof keypair for signing certificates
        from .proof import ProofManager

        proof_manager = ProofManager(self.root)
        proof_manager.generate_keypair()

        return True

    def is_initialized(self) -> bool:
        """Verificar si el repositorio está inicializado."""
        return self.root.exists() and self.objects_dir.exists()

    # === Object Storage ===

    def _object_path(self, obj_type: ObjectType, obj_hash: str) -> Path:
        """Obtener path de almacenamiento para un objeto."""
        prefix = self.OBJECT_PREFIXES[obj_type]
        dir_part, file_part = hash_to_path(obj_hash)
        return self.objects_dir / prefix / dir_part / file_part

    def store(self, obj: TruthObject) -> str:
        """
        Almacenar un objeto en el repositorio.

        Returns:
            Hash del objeto almacenado
        """
        obj_hash = obj.hash
        obj_path = self._object_path(obj.object_type, obj_hash)

        # Crear directorio si no existe
        obj_path.parent.mkdir(parents=True, exist_ok=True)

        # Serializar y comprimir
        serialized = obj.serialize()
        compressed = zlib.compress(serialized.encode("utf-8"))

        # Escribir
        obj_path.write_bytes(compressed)

        return obj_hash

    def load(self, obj_type: ObjectType, obj_hash: str) -> TruthObject | None:
        """
        Cargar un objeto del repositorio.

        Returns:
            Objeto deserializado o None si no existe
        """
        obj_path = self._object_path(obj_type, obj_hash)

        if not obj_path.exists():
            return None

        # Leer y descomprimir
        compressed = obj_path.read_bytes()
        serialized = zlib.decompress(compressed).decode("utf-8")

        return TruthObject.deserialize(serialized)

    def exists(self, obj_type: ObjectType, obj_hash: str) -> bool:
        """Verificar si un objeto existe."""
        return self._object_path(obj_type, obj_hash).exists()

    def delete(self, obj_type: ObjectType, obj_hash: str) -> bool:
        """Eliminar un objeto (usar con precaución)."""
        obj_path = self._object_path(obj_type, obj_hash)
        if obj_path.exists():
            obj_path.unlink()
            return True
        return False

    # === Index (Staging Area) ===

    def _read_index(self) -> dict:
        """Leer el index."""
        if not self.index_file.exists():
            return {"staged": [], "timestamp": None}
        return json.loads(self.index_file.read_text())

    def _write_index(self, index: dict):
        """Escribir el index."""
        self.index_file.write_text(json.dumps(index, indent=2))

    def stage(self, obj: TruthObject) -> str:
        """
        Agregar objeto al staging area.

        Similar a `git add`.
        """
        # Almacenar el objeto
        obj_hash = self.store(obj)

        # Agregar al index
        index = self._read_index()
        staged_item = {
            "hash": obj_hash,
            "type": obj.object_type.value,
            "added_at": datetime.now().isoformat(),
        }

        # Evitar duplicados
        if not any(s["hash"] == obj_hash for s in index["staged"]):
            index["staged"].append(staged_item)
            index["timestamp"] = datetime.now().isoformat()
            self._write_index(index)

        return obj_hash

    def unstage(self, obj_hash: str) -> bool:
        """Remover objeto del staging area."""
        index = self._read_index()
        original_len = len(index["staged"])
        index["staged"] = [s for s in index["staged"] if s["hash"] != obj_hash]

        if len(index["staged"]) < original_len:
            self._write_index(index)
            return True
        return False

    def get_staged(self) -> list[dict]:
        """Obtener objetos en staging."""
        return self._read_index()["staged"]

    def clear_staging(self):
        """Limpiar staging area."""
        self._write_index({"staged": [], "timestamp": datetime.now().isoformat()})

    # === References ===

    def _ref_path(self, ref_name: str) -> Path:
        """Obtener path de una referencia."""
        return self.refs_dir / ref_name

    def set_ref(self, ref_name: str, obj_hash: str):
        """Establecer una referencia a un hash."""
        ref_path = self._ref_path(ref_name)
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(obj_hash + "\n")

    def get_ref(self, ref_name: str) -> str | None:
        """Obtener el hash de una referencia."""
        ref_path = self._ref_path(ref_name)
        if not ref_path.exists():
            return None
        return ref_path.read_text().strip()

    def delete_ref(self, ref_name: str) -> bool:
        """Eliminar una referencia."""
        ref_path = self._ref_path(ref_name)
        if ref_path.exists():
            ref_path.unlink()
            return True
        return False

    def list_refs(self, prefix: str = "") -> list[tuple[str, str]]:
        """Listar referencias con su hash."""
        refs = []
        search_dir = self.refs_dir / prefix if prefix else self.refs_dir

        if not search_dir.exists():
            return refs

        for ref_file in search_dir.rglob("*"):
            if ref_file.is_file():
                ref_name = str(ref_file.relative_to(self.refs_dir))
                ref_hash = ref_file.read_text().strip()
                refs.append((ref_name, ref_hash))

        return refs

    # === HEAD ===

    def get_head(self) -> str | None:
        """Obtener el hash al que apunta HEAD."""
        if not self.head_file.exists():
            return None

        content = self.head_file.read_text().strip()

        # Si es una referencia simbólica
        if content.startswith("ref: "):
            ref_name = content[5:]
            return self.get_ref(ref_name)

        # Si es un hash directo
        return content

    def set_head(self, target: str, symbolic: bool = True):
        """
        Establecer HEAD.

        Args:
            target: Nombre de ref (si symbolic) o hash directo
            symbolic: Si True, crea referencia simbólica
        """
        if symbolic:
            self.head_file.write_text(f"ref: {target}\n")
        else:
            self.head_file.write_text(f"{target}\n")

    # === High-Level Operations ===

    def claim(
        self,
        content: str,
        sources: list[dict] = None,
        confidence: float = 0.5,
        domain: str = "general",
        category: str = "factual",
        created_by: str = "",
    ) -> Claim:
        """
        Crear y stagear un nuevo claim.

        Similar a crear un archivo y hacer `git add`.
        """
        from .objects import ClaimCategory, Source

        claim = Claim(
            content=content,
            confidence=confidence,
            category=ClaimCategory(category),
            domain=domain,
            sources=[
                Source(
                    url=s.get("url", ""),
                    title=s.get("title", ""),
                    source_type=s.get("type", "PRIMARY"),
                    reliability=s.get("reliability", 0.8),
                )
                for s in (sources or [])
            ],
            created_by=created_by,
        )

        self.stage(claim)
        return claim

    def axiom(
        self,
        content: str,
        axiom_type: str,
        domain: str,
        authority_source: str,
        authority_reference: str = "",
    ) -> Axiom:
        """Crear y stagear un nuevo axiom."""
        from .objects import AxiomType

        axiom = Axiom(
            content=content,
            axiom_type=AxiomType(axiom_type),
            domain=domain,
            authority_source=authority_source,
            authority_reference=authority_reference,
        )

        self.stage(axiom)
        return axiom

    def verify(
        self,
        verifier_results: dict[str, tuple[float, str]],
        trigger: str = "manual",
        session_id: str = "",
        use_ontological: bool = True,
        claim_content: str = "",
        claim_domain: str = "general",
    ) -> Verification | None:
        """
        Verificar los claims stageados y crear un commit.

        Args:
            verifier_results: {"CLAUDE": (0.85, "reasoning"), ...}
            trigger: Qué disparó la verificación
            session_id: ID de sesión (opcional)
            use_ontological: Use ontological consensus (default True)
            claim_content: Claim text for ontological analysis
            claim_domain: Domain for ontological analysis

        Returns:
            Verification creada o None si no hay nada stageado
        """
        staged = self.get_staged()
        if not staged:
            return None

        # Crear context con los claims stageados
        claim_refs = []
        axiom_hashes = []

        for item in staged:
            if item["type"] == ObjectType.CLAIM.value:
                claim_refs.append(ClaimRef(hash=item["hash"], role="PRIMARY"))
            elif item["type"] == ObjectType.AXIOM.value:
                axiom_hashes.append(item["hash"])

        context = Context(
            name=f"Verification {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            domain="verified",
            claims=claim_refs,
            axioms=axiom_hashes,
            created_by="TruthRepository",
        )
        context_hash = self.store(context)

        # Crear votos de verificadores
        verifiers = {}
        confidences = {}

        for verifier, (confidence, reasoning) in verifier_results.items():
            verifiers[verifier] = VerifierVote(
                roles=["VERIFIER"],
                confidence=confidence,
                reasoning=reasoning,
                claims_reviewed=len(claim_refs),
                claims_approved=int(len(claim_refs) * confidence),
            )
            confidences[verifier] = confidence

        # Calcular consenso
        config = self._read_config()
        threshold = config.get("consensus_threshold", 0.66)

        # Legacy consensus (always calculated for backwards compat)
        consensus = calculate_consensus(confidences, threshold)

        # Ontological consensus (v0.5.0+)
        ontological_consensus = None
        if use_ontological:
            from .ontological_classifier import calculate_ontological_consensus

            ontological_consensus = calculate_ontological_consensus(
                claim=claim_content,
                validator_results=verifier_results,
                threshold=threshold,
                domain=claim_domain,
            )

        # Obtener parent (última verification)
        parent_hash = self.get_head()

        # Crear verification
        verification = Verification(
            context_hash=context_hash,
            parent_hash=parent_hash,
            verifiers=verifiers,
            consensus=consensus,
            trigger=trigger,
            session_id=session_id,
            ontological_consensus=ontological_consensus,
        )
        verification_hash = self.store(verification)

        # Actualizar referencias
        for verifier in verifiers:
            self.set_ref(f"perspectives/{verifier}", verification_hash)

        # Determine if we should update consensus/main
        # With ontological consensus:
        #   - PASSED: update (consensus achieved)
        #   - UNRESOLVABLE (MYSTERY): update (preserved as data)
        #   - PENDING_MEDIATION (GAP): do NOT update (waiting for human)
        #   - FAILED: do NOT update
        should_update_consensus = False
        if ontological_consensus:
            from .ontological_classifier import ConsensusStatus

            should_update_consensus = ontological_consensus.status in (
                ConsensusStatus.PASSED,
                ConsensusStatus.UNRESOLVABLE,  # MYSTERY is valuable data
            )
        else:
            should_update_consensus = consensus.passed

        if should_update_consensus:
            self.set_ref("consensus/main", verification_hash)

        # Limpiar staging
        self.clear_staging()

        return verification

    def history(
        self,
        ref: str = "consensus/main",
        limit: int = 10,
    ) -> list[Verification]:
        """
        Obtener historial de verificaciones.

        Similar a `git log`.
        """
        history = []
        current_hash = self.get_ref(ref)

        while current_hash and len(history) < limit:
            verification = self.load(ObjectType.VERIFICATION, current_hash)
            if not verification:
                break

            history.append(verification)
            current_hash = verification.parent_hash

        return history

    def status(self) -> dict:
        """
        Obtener estado del repositorio.

        Similar a `git status`.
        """
        staged = self.get_staged()
        head = self.get_head()
        perspectives = self.list_refs("perspectives")
        consensus_ref = self.get_ref("consensus/main")

        return {
            "initialized": self.is_initialized(),
            "staged_count": len(staged),
            "staged": staged,
            "head": head,
            "perspectives": dict(perspectives),
            "consensus": consensus_ref,
        }

    def _read_config(self) -> dict:
        """Leer configuración."""
        if not self.config_file.exists():
            return {}
        return json.loads(self.config_file.read_text())

    # === Iteration ===

    def iter_objects(self, obj_type: ObjectType) -> Iterator[TruthObject]:
        """Iterar sobre todos los objetos de un tipo."""
        prefix = self.OBJECT_PREFIXES[obj_type]
        prefix_dir = self.objects_dir / prefix

        if not prefix_dir.exists():
            return

        for dir_entry in prefix_dir.iterdir():
            if dir_entry.is_dir():
                for file_entry in dir_entry.iterdir():
                    obj_hash = path_to_hash(dir_entry.name, file_entry.name)
                    obj = self.load(obj_type, obj_hash)
                    if obj:
                        yield obj

    def count_objects(self) -> dict[str, int]:
        """Contar objetos por tipo."""
        counts = {}
        for obj_type in ObjectType:
            count = sum(1 for _ in self.iter_objects(obj_type))
            counts[obj_type.value] = count
        return counts

    # === Lookup helpers ===

    def get_object(self, obj_type: ObjectType, obj_hash: str) -> dict | None:
        """Get object as dictionary by exact hash."""
        obj = self.load(obj_type, obj_hash)
        if obj:
            data = json.loads(obj.serialize())
            data["$hash"] = obj_hash
            return data
        return None

    def get_object_by_prefix(self, prefix: str) -> tuple[ObjectType, dict] | None:
        """
        Find object by hash prefix (like git).

        Returns:
            Tuple of (object_type, object_data) or None
        """
        prefix = prefix.lower()

        for obj_type in ObjectType:
            type_prefix = self.OBJECT_PREFIXES[obj_type]
            type_dir = self.objects_dir / type_prefix

            if not type_dir.exists():
                continue

            # Check each subdirectory
            for dir_entry in type_dir.iterdir():
                if not dir_entry.is_dir():
                    continue

                for file_entry in dir_entry.iterdir():
                    obj_hash = path_to_hash(dir_entry.name, file_entry.name)
                    if obj_hash.startswith(prefix):
                        obj = self.get_object(obj_type, obj_hash)
                        if obj:
                            return (obj_type, obj)

        return None

    def find_verifications_for_claim(self, claim_hash: str) -> list[dict]:
        """
        Find all verifications that include a specific claim.

        Returns:
            List of verification dicts, ordered by timestamp
        """
        results = []

        for verification in self.iter_objects(ObjectType.VERIFICATION):
            v_data = json.loads(verification.serialize())
            v_hash = verification.compute_hash()
            v_data["$hash"] = v_hash

            # Check if this verification's context includes our claim
            context_hash = v_data.get("context", "")
            context = self.get_object(ObjectType.CONTEXT, context_hash)

            if context:
                # Claims can be strings or dicts with 'hash' key
                claim_hashes = []
                for c in context.get("claims", []):
                    if isinstance(c, dict):
                        claim_hashes.append(c.get("hash", ""))
                    else:
                        claim_hashes.append(c)

                if claim_hash in claim_hashes:
                    results.append(v_data)

        # Sort by timestamp
        results.sort(key=lambda v: v.get("metadata", {}).get("timestamp", ""))

        return results


# === Tests ===


def _test_repository():
    """Pruebas del repositorio."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / ".truth"
        repo = TruthRepository(str(repo_path))

        # Test init
        repo.init()
        assert repo.is_initialized()
        print("✅ Repository initialized")

        # Test claim
        claim = repo.claim(
            content="Python fue creado por Guido van Rossum",
            sources=[{"url": "https://python.org/about", "title": "About Python"}],
            confidence=0.9,
            domain="programming.history",
        )
        print(f"✅ Claim created: {claim.short_hash}")

        # Test staging
        staged = repo.get_staged()
        assert len(staged) == 1
        print(f"✅ Staging works: {len(staged)} items")

        # Test verify
        verification = repo.verify(
            verifier_results={
                "CLAUDE": (0.88, "Verified against python.org"),
                "GPT": (0.85, "Cross-referenced with Wikipedia"),
                "GRAVITY": (0.87, "Synthesis of perspectives"),
            },
            trigger="test",
        )
        assert verification is not None
        assert verification.consensus.passed
        print(f"✅ Verification created: {verification.short_hash}")
        print(f"   Consensus: {verification.consensus.value:.2%}")

        # Test history
        history = repo.history()
        assert len(history) == 1
        print(f"✅ History works: {len(history)} verifications")

        # Test status
        status = repo.status()
        assert status["staged_count"] == 0  # Cleared after verify
        assert status["consensus"] is not None
        print("✅ Status works")

        # Test count
        counts = repo.count_objects()
        print(f"✅ Object counts: {counts}")

        print("\n✅ All repository tests passed")


if __name__ == "__main__":
    _test_repository()
