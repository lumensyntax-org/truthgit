"""
TruthGit Proof - Cryptographic certificates for verified claims.

Generates portable, verifiable proofs that a claim reached consensus.
Uses Ed25519 signatures for security and compactness.

Usage:
    $ truthgit prove <hash>      # Generate proof certificate
    $ truthgit verify-proof <certificate>  # Verify a proof

Certificate Format:
    {
        "version": "1.0",
        "claim": { ... },
        "verification": { ... },
        "signature": "base64...",
        "public_key": "base64..."
    }
"""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass
class ProofCertificate:
    """A cryptographic proof that a claim was verified."""

    version: str
    claim_hash: str
    claim_content: str
    claim_domain: str
    verification_hash: str
    consensus_value: float
    consensus_passed: bool
    validators: list[str]
    timestamp: str
    signature: str
    public_key: str
    repo_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "claim": {
                "hash": self.claim_hash,
                "content": self.claim_content,
                "domain": self.claim_domain,
            },
            "verification": {
                "hash": self.verification_hash,
                "consensus": self.consensus_value,
                "passed": self.consensus_passed,
                "validators": self.validators,
                "timestamp": self.timestamp,
            },
            "proof": {
                "signature": self.signature,
                "public_key": self.public_key,
                "repo_id": self.repo_id,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_compact(self) -> str:
        """Return compact base64 encoded certificate."""
        data = json.dumps(self.to_dict(), separators=(",", ":"))
        return base64.urlsafe_b64encode(data.encode()).decode()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProofCertificate":
        return cls(
            version=data["version"],
            claim_hash=data["claim"]["hash"],
            claim_content=data["claim"]["content"],
            claim_domain=data["claim"]["domain"],
            verification_hash=data["verification"]["hash"],
            consensus_value=data["verification"]["consensus"],
            consensus_passed=data["verification"]["passed"],
            validators=data["verification"]["validators"],
            timestamp=data["verification"]["timestamp"],
            signature=data["proof"]["signature"],
            public_key=data["proof"]["public_key"],
            repo_id=data["proof"].get("repo_id", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ProofCertificate":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_compact(cls, compact: str) -> "ProofCertificate":
        """Parse compact base64 encoded certificate."""
        data = base64.urlsafe_b64decode(compact.encode()).decode()
        return cls.from_json(data)


class ProofManager:
    """Manages cryptographic proofs for a TruthGit repository."""

    PRIVATE_KEY_FILE = "proof.key"
    PUBLIC_KEY_FILE = "proof.pub"
    PROOF_VERSION = "1.0"

    def __init__(self, repo_path: str | Path = ".truth"):
        self.repo_path = Path(repo_path)
        self._private_key: Ed25519PrivateKey | None = None
        self._public_key: Ed25519PublicKey | None = None

    @property
    def keys_exist(self) -> bool:
        """Check if keypair exists."""
        return (self.repo_path / self.PRIVATE_KEY_FILE).exists() and (
            self.repo_path / self.PUBLIC_KEY_FILE
        ).exists()

    def generate_keypair(self, force: bool = False) -> tuple[str, str]:
        """
        Generate new Ed25519 keypair for signing proofs.

        Returns:
            Tuple of (private_key_path, public_key_path)
        """
        if self.keys_exist and not force:
            raise FileExistsError("Keypair already exists. Use force=True to regenerate.")

        # Generate new keypair
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize keys
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Write to files
        private_path = self.repo_path / self.PRIVATE_KEY_FILE
        public_path = self.repo_path / self.PUBLIC_KEY_FILE

        private_path.write_bytes(private_bytes)
        private_path.chmod(0o600)  # Restrict access
        public_path.write_bytes(public_bytes)

        self._private_key = private_key
        self._public_key = public_key

        return str(private_path), str(public_path)

    def load_keys(self) -> None:
        """Load existing keypair from disk."""
        if not self.keys_exist:
            raise FileNotFoundError("No keypair found. Run 'truthgit init' first.")

        private_path = self.repo_path / self.PRIVATE_KEY_FILE
        public_path = self.repo_path / self.PUBLIC_KEY_FILE

        self._private_key = serialization.load_pem_private_key(
            private_path.read_bytes(),
            password=None,
        )
        self._public_key = serialization.load_pem_public_key(
            public_path.read_bytes(),
        )

    def get_public_key_b64(self) -> str:
        """Get public key as base64 string."""
        if not self._public_key:
            self.load_keys()

        raw_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.urlsafe_b64encode(raw_bytes).decode()

    def get_repo_id(self) -> str:
        """Get repository ID (first 16 chars of public key hash)."""
        from .hashing import content_hash

        return content_hash(self.get_public_key_b64())[:16]

    def sign(self, data: str) -> str:
        """Sign data with private key, return base64 signature."""
        if not self._private_key:
            self.load_keys()

        signature = self._private_key.sign(data.encode())
        return base64.urlsafe_b64encode(signature).decode()

    def verify_signature(self, data: str, signature_b64: str, public_key_b64: str) -> bool:
        """Verify a signature against data and public key."""
        try:
            signature = base64.urlsafe_b64decode(signature_b64.encode())
            public_key_bytes = base64.urlsafe_b64decode(public_key_b64.encode())

            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, data.encode())
            return True
        except Exception:
            return False

    def create_proof(
        self,
        claim_hash: str,
        claim_content: str,
        claim_domain: str,
        verification_hash: str,
        consensus_value: float,
        consensus_passed: bool,
        validators: list[str],
        timestamp: str | None = None,
    ) -> ProofCertificate:
        """
        Create a signed proof certificate for a verified claim.
        """
        if not self._private_key:
            self.load_keys()

        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + "Z"

        # Data to sign (canonical JSON)
        sign_data = json.dumps(
            {
                "v": self.PROOF_VERSION,
                "ch": claim_hash,
                "cc": claim_content,
                "cd": claim_domain,
                "vh": verification_hash,
                "cv": consensus_value,
                "cp": consensus_passed,
                "vs": validators,
                "ts": timestamp,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

        signature = self.sign(sign_data)
        public_key = self.get_public_key_b64()
        repo_id = self.get_repo_id()

        return ProofCertificate(
            version=self.PROOF_VERSION,
            claim_hash=claim_hash,
            claim_content=claim_content,
            claim_domain=claim_domain,
            verification_hash=verification_hash,
            consensus_value=consensus_value,
            consensus_passed=consensus_passed,
            validators=validators,
            timestamp=timestamp,
            signature=signature,
            public_key=public_key,
            repo_id=repo_id,
        )

    def verify_proof(self, cert: ProofCertificate) -> tuple[bool, str]:
        """
        Verify a proof certificate.

        Returns:
            Tuple of (is_valid, message)
        """
        # Reconstruct signed data
        sign_data = json.dumps(
            {
                "v": cert.version,
                "ch": cert.claim_hash,
                "cc": cert.claim_content,
                "cd": cert.claim_domain,
                "vh": cert.verification_hash,
                "cv": cert.consensus_value,
                "cp": cert.consensus_passed,
                "vs": cert.validators,
                "ts": cert.timestamp,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

        # Verify signature
        is_valid = self.verify_signature(sign_data, cert.signature, cert.public_key)

        if not is_valid:
            return False, "Invalid signature"

        if not cert.consensus_passed:
            return True, "Signature valid, but consensus did NOT pass"

        num_validators = len(cert.validators)
        pct = f"{cert.consensus_value:.0%}"
        return True, f"Valid proof: {pct} consensus from {num_validators} validators"


def verify_proof_standalone(cert_data: str | dict) -> tuple[bool, str, ProofCertificate | None]:
    """
    Verify a proof certificate without needing a repository.

    Args:
        cert_data: JSON string, dict, or compact base64 certificate

    Returns:
        Tuple of (is_valid, message, certificate)
    """
    try:
        # Parse certificate
        if isinstance(cert_data, dict):
            cert = ProofCertificate.from_dict(cert_data)
        elif cert_data.startswith("{"):
            cert = ProofCertificate.from_json(cert_data)
        else:
            cert = ProofCertificate.from_compact(cert_data)

        # Create temporary manager for verification
        manager = ProofManager.__new__(ProofManager)
        manager._private_key = None
        manager._public_key = None

        is_valid, message = manager.verify_proof(cert)
        return is_valid, message, cert

    except Exception as e:
        return False, f"Failed to parse certificate: {e}", None
