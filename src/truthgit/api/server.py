"""
TruthGit FastAPI Server
Production-ready API for claim verification and proof generation.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from truthgit.repository import TruthRepository
from truthgit.validators import OllamaValidator, ClaudeValidator, GPTValidator, get_default_validators
from truthgit.proof import ProofManager, verify_proof_standalone


def load_repo_config(repo: TruthRepository) -> dict:
    """Load config from repository's config file."""
    if repo.config_file.exists():
        with open(repo.config_file) as f:
            return json.load(f)
    return {}


# Request/Response Models
class VerifyRequest(BaseModel):
    claim: str = Field(..., min_length=1, description="The claim to verify")
    domain: str = Field(default="general", description="Knowledge domain")


class ProveRequest(BaseModel):
    claim: str = Field(..., min_length=1, description="The claim to prove")
    domain: str = Field(default="general", description="Knowledge domain")
    format: str = Field(default="json", pattern="^(json|compact)$")


class VerifyProofRequest(BaseModel):
    certificate: dict | str = Field(..., description="Certificate to verify")


class SearchParams(BaseModel):
    query: str = Field(..., min_length=1)
    domain: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


class ValidatorResult(BaseModel):
    name: str
    confidence: float
    reasoning: str


class VerificationResponse(BaseModel):
    passed: bool
    consensus: float
    validators: list[ValidatorResult]
    claimHash: str
    timestamp: str


class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    meta: dict


# Global repository instance
repo: Optional[TruthRepository] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize repository on startup."""
    global repo
    repo = TruthRepository()
    if not repo.is_initialized():
        repo.init()
    yield
    # Cleanup if needed


# Create FastAPI app
app = FastAPI(
    title="TruthGit API",
    description="Version control for verified truth. Verify claims using multi-validator AI consensus.",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_response(data: dict = None, error: str = None, start_time: float = None) -> dict:
    """Create standardized API response."""
    processing_time = int((time.time() - start_time) * 1000) if start_time else 0
    return {
        "success": error is None,
        "data": data,
        "error": error,
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "processingTime": processing_time,
        },
    }


@app.get("/")
async def root():
    """API root - health check."""
    return {
        "name": "TruthGit API",
        "version": "0.4.0",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/api/status")
async def get_status():
    """Get repository status."""
    start_time = time.time()

    try:
        if not repo or not repo.is_initialized():
            return create_response(
                data={
                    "initialized": False,
                    "objectCounts": {"claims": 0, "axioms": 0, "verifications": 0, "contexts": 0},
                    "consensusThreshold": 0.66,
                    "repoId": "",
                },
                start_time=start_time,
            )

        # Count objects using the repository method
        counts = {"claims": 0, "axioms": 0, "verifications": 0, "contexts": 0}

        try:
            object_counts = repo.count_objects()
            counts["claims"] = object_counts.get("claim", 0)
            counts["axioms"] = object_counts.get("axiom", 0)
            counts["verifications"] = object_counts.get("verification", 0)
            counts["contexts"] = object_counts.get("context", 0)
        except Exception:
            pass  # Use default zero counts

        config = load_repo_config(repo)
        return create_response(
            data={
                "initialized": True,
                "objectCounts": counts,
                "consensusThreshold": config.get("consensus_threshold", 0.66),
                "repoId": config.get("repo_id", ""),
            },
            start_time=start_time,
        )
    except Exception as e:
        return create_response(error=str(e), start_time=start_time)


@app.post("/api/verify")
async def verify_claim(request: VerifyRequest):
    """Verify a claim using multi-validator consensus."""
    start_time = time.time()

    try:
        if not repo:
            raise HTTPException(status_code=500, detail="Repository not initialized")

        # Create claim first
        claim = repo.claim(
            content=request.claim,
            domain=request.domain,
            category="factual",
        )

        # Create validators - use cloud if available, fallback to Ollama
        validators = get_default_validators(local_only=False)
        if not validators:
            # Fallback to explicit validators
            validators = [
                ClaudeValidator(),
                GPTValidator(),
            ]
            validators = [v for v in validators if v.is_available()]
        if not validators:
            # Last resort: try Ollama
            validators = [
                OllamaValidator(model="hermes3"),
                OllamaValidator(model="nemotron-mini"),
            ]

        # Run each validator and collect results
        verifier_results: dict[str, tuple[float, str]] = {}
        validator_details = []

        for validator in validators:
            try:
                result = validator.validate(request.claim, request.domain)
                verifier_results[result.validator_name] = (result.confidence, result.reasoning)
                validator_details.append({
                    "name": result.validator_name,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning[:200] + "..." if len(result.reasoning) > 200 else result.reasoning,
                })
            except Exception as e:
                # Skip failed validators
                continue

        if len(verifier_results) < 2:
            return create_response(
                error="Verification failed - insufficient validators available",
                start_time=start_time,
            )

        # Run verification with collected results
        verification = repo.verify(verifier_results=verifier_results)

        if not verification:
            return create_response(
                error="Verification failed",
                start_time=start_time,
            )

        return create_response(
            data={
                "passed": verification.consensus.passed,
                "consensus": verification.consensus.value,
                "validators": validator_details,
                "claimHash": claim.hash[:8],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            start_time=start_time,
        )

    except Exception as e:
        return create_response(error=str(e), start_time=start_time)


@app.post("/api/prove")
async def generate_proof(request: ProveRequest):
    """Generate a cryptographic proof certificate."""
    start_time = time.time()

    try:
        if not repo:
            raise HTTPException(status_code=500, detail="Repository not initialized")

        # First verify the claim
        claim = repo.claim(
            content=request.claim,
            domain=request.domain,
            category="factual",
        )

        # Create validators - use cloud if available, fallback to Ollama
        validators = get_default_validators(local_only=False)
        if not validators:
            validators = [ClaudeValidator(), GPTValidator()]
            validators = [v for v in validators if v.is_available()]
        if not validators:
            validators = [OllamaValidator(model="hermes3"), OllamaValidator(model="nemotron-mini")]

        # Run each validator and collect results
        verifier_results: dict[str, tuple[float, str]] = {}
        validator_names = []

        for validator in validators:
            try:
                result = validator.validate(request.claim, request.domain)
                verifier_results[result.validator_name] = (result.confidence, result.reasoning)
                validator_names.append(result.validator_name)
            except Exception:
                continue

        if len(verifier_results) < 2:
            return create_response(
                error="Verification failed - insufficient validators available",
                start_time=start_time,
            )

        verification = repo.verify(verifier_results=verifier_results)

        if not verification or not verification.consensus.passed:
            return create_response(
                error="Claim did not pass verification",
                start_time=start_time,
            )

        # Generate proof certificate using ProofManager
        proof_manager = ProofManager(repo.root)
        if not proof_manager.keys_exist:
            proof_manager.generate_keypair()

        certificate = proof_manager.create_proof(
            claim_hash=claim.hash,
            claim_content=claim.content,
            claim_domain=claim.domain,
            verification_hash=verification.hash,
            consensus_value=verification.consensus.value,
            consensus_passed=verification.consensus.passed,
            validators=validator_names,
        )

        if request.format == "compact":
            return create_response(
                data={"certificate": certificate.to_compact()},
                start_time=start_time,
            )

        return create_response(
            data={"certificate": certificate.to_dict()},
            start_time=start_time,
        )

    except Exception as e:
        return create_response(error=str(e), start_time=start_time)


@app.post("/api/verify-proof")
async def verify_proof_endpoint(request: VerifyProofRequest):
    """Verify a proof certificate."""
    start_time = time.time()

    try:
        is_valid, message, cert = verify_proof_standalone(request.certificate)

        if cert is None:
            return create_response(
                data={
                    "valid": False,
                    "message": message,
                    "claim": {},
                    "verification": {},
                },
                start_time=start_time,
            )

        return create_response(
            data={
                "valid": is_valid,
                "message": message,
                "claim": {
                    "content": cert.claim_content,
                    "domain": cert.claim_domain,
                },
                "verification": {
                    "consensus": cert.consensus_value,
                    "validators": cert.validators,
                    "timestamp": cert.timestamp,
                },
            },
            start_time=start_time,
        )

    except Exception as e:
        return create_response(error=str(e), start_time=start_time)


@app.get("/api/search")
async def search_claims(query: str, domain: Optional[str] = None, limit: int = 10):
    """Search for verified claims."""
    start_time = time.time()

    try:
        if not repo:
            raise HTTPException(status_code=500, detail="Repository not initialized")

        results = repo.search(query=query, domain=domain, limit=limit)

        claims = []
        for result in results:
            claims.append({
                "hash": result.hash[:8] if hasattr(result, 'hash') else "",
                "content": result.content if hasattr(result, 'content') else str(result),
                "domain": result.domain if hasattr(result, 'domain') else "general",
                "consensus": result.consensus if hasattr(result, 'consensus') else 0,
                "status": result.status.value if hasattr(result, 'status') else "VERIFIED",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

        return create_response(data=claims, start_time=start_time)

    except Exception as e:
        return create_response(data=[], start_time=start_time)


@app.get("/api/claims")
async def get_recent_claims(limit: int = 10):
    """Get recent claims."""
    start_time = time.time()

    try:
        if not repo:
            return create_response(data=[], start_time=start_time)

        # Get recent verifications
        results = repo.log(limit=limit)

        claims = []
        for result in results:
            claims.append({
                "hash": result.get("hash", "")[:8],
                "content": result.get("content", ""),
                "domain": result.get("domain", "general"),
                "consensus": result.get("consensus", 0),
                "status": result.get("status", "VERIFIED"),
                "timestamp": result.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            })

        return create_response(data=claims, start_time=start_time)

    except Exception as e:
        return create_response(data=[], start_time=start_time)


def run():
    """Run the server."""
    import uvicorn
    uvicorn.run(
        "truthgit.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    run()
