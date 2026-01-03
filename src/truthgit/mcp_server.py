"""
TruthGit MCP Server - Model Context Protocol integration.

Allows AI assistants (Claude, Cursor, etc.) to verify claims and
generate proofs while working.

Usage:
    # Run directly
    python -m truthgit.mcp_server

    # Or via entry point
    truthgit-mcp

Configuration for Claude Code (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "truthgit": {
          "command": "truthgit-mcp",
          "args": []
        }
      }
    }
"""

import asyncio
import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)


def create_server() -> Server:
    """Create and configure the TruthGit MCP server."""
    server = Server("truthgit")

    # Store repo path (can be configured)
    repo_path = Path.cwd() / ".truth"

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available TruthGit tools."""
        return [
            Tool(
                name="truthgit_verify_claim",
                description=(
                    "Verify a claim using multi-validator AI consensus. "
                    "Returns confidence score and reasoning from multiple validators."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "The statement to verify",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Knowledge domain (physics, history, etc)",
                            "default": "general",
                        },
                    },
                    "required": ["claim"],
                },
            ),
            Tool(
                name="truthgit_prove",
                description=(
                    "Generate a cryptographic proof certificate for a verified claim. "
                    "The certificate can be shared and verified by anyone."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "The claim to prove (must be verified first)",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Knowledge domain",
                            "default": "general",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "compact"],
                            "description": "Output format (json or compact base64)",
                            "default": "json",
                        },
                    },
                    "required": ["claim"],
                },
            ),
            Tool(
                name="truthgit_verify_proof",
                description=(
                    "Verify a proof certificate. Works without access to the original repository."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "certificate": {
                            "type": "string",
                            "description": "The proof certificate (JSON or compact base64)",
                        },
                    },
                    "required": ["certificate"],
                },
            ),
            Tool(
                name="truthgit_search",
                description=("Search for verified claims in the repository."),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (matches claim content)",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Filter by domain",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="truthgit_status",
                description="Show TruthGit repository status.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""

        if name == "truthgit_verify_claim":
            return await _verify_claim(
                arguments.get("claim", ""),
                arguments.get("domain", "general"),
                repo_path,
            )

        elif name == "truthgit_prove":
            return await _prove_claim(
                arguments.get("claim", ""),
                arguments.get("domain", "general"),
                arguments.get("format", "json"),
                repo_path,
            )

        elif name == "truthgit_verify_proof":
            return await _verify_proof(arguments.get("certificate", ""))

        elif name == "truthgit_search":
            return await _search_claims(
                arguments.get("query", ""),
                arguments.get("domain"),
                arguments.get("limit", 10),
                repo_path,
            )

        elif name == "truthgit_status":
            return await _get_status(repo_path)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def _verify_claim(claim: str, domain: str, repo_path: Path) -> list[TextContent]:
    """Verify a claim with multi-validator consensus."""
    try:
        from .repository import TruthRepository
        from .validators import get_default_validators

        # Initialize repo if needed
        repo = TruthRepository(str(repo_path))
        if not repo.is_initialized():
            repo.init()

        # Get validators
        validators = get_default_validators(local_only=True)
        if len(validators) < 2:
            # Try with cloud validators
            validators = get_default_validators(local_only=False)

        if len(validators) < 2:
            return [
                TextContent(
                    type="text",
                    text="Error: Need at least 2 validators. Install Ollama or set API keys.",
                )
            ]

        # Verify claim
        results = []
        for v in validators:
            result = v.validate(claim, domain)
            results.append(
                {
                    "validator": v.name,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "error": result.error,
                }
            )

        # Calculate consensus
        successful = [r for r in results if not r["error"]]
        if successful:
            avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
            passed = avg_confidence >= 0.66
        else:
            avg_confidence = 0
            passed = False

        # Create claim in repo
        claim_obj = repo.claim(content=claim, domain=domain, confidence=avg_confidence)

        status = "PASSED" if passed else "FAILED"
        text = f"""## Claim Verification: {status}

**Claim:** {claim}
**Domain:** {domain}
**Consensus:** {round(avg_confidence * 100)}%

### Validator Results:
"""
        for r in results:
            if r["error"]:
                text += f"- **{r['validator']}**: Error - {r['error']}\n"
            else:
                pct = round(r["confidence"] * 100)
                reason = r["reasoning"][:100]
                text += f"- **{r['validator']}**: {pct}% - {reason}...\n"

        text += f"\n**Claim Hash:** `{claim_obj.short_hash}`"

        return [TextContent(type="text", text=text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error verifying claim: {e}")]


async def _prove_claim(claim: str, domain: str, format: str, repo_path: Path) -> list[TextContent]:
    """Generate proof certificate for a claim."""
    try:
        from .proof import ProofManager
        from .repository import TruthRepository
        from .validators import get_default_validators

        repo = TruthRepository(str(repo_path))
        if not repo.is_initialized():
            return [
                TextContent(
                    type="text",
                    text="Error: No TruthGit repository. Run truthgit init first.",
                )
            ]

        # Verify the claim first
        validators = get_default_validators(local_only=True)
        if len(validators) < 2:
            validators = get_default_validators(local_only=False)

        results = []
        for v in validators[:3]:  # Limit to 3 validators
            result = v.validate(claim, domain)
            results.append(result)

        successful = [r for r in results if r.success]
        if not successful:
            return [TextContent(type="text", text="Error: No validators could verify the claim.")]

        avg_confidence = sum(r.confidence for r in successful) / len(successful)
        passed = avg_confidence >= 0.66

        # Create proof
        proof_manager = ProofManager(repo.root)
        from datetime import datetime

        from .hashing import content_hash

        claim_hash = content_hash(claim)
        verification_hash = content_hash(f"{claim_hash}:{datetime.utcnow().isoformat()}")

        cert = proof_manager.create_proof(
            claim_hash=claim_hash,
            claim_content=claim,
            claim_domain=domain,
            verification_hash=verification_hash,
            consensus_value=avg_confidence,
            consensus_passed=passed,
            validators=[r.validator_name for r in successful],
        )

        if format == "compact":
            output = cert.to_compact()
        else:
            output = cert.to_json()

        status = "PASSED" if passed else "FAILED"
        text = f"""## Proof Certificate Generated: {status}

**Claim:** {claim}
**Consensus:** {round(avg_confidence * 100)}%
**Repo ID:** {cert.repo_id}

### Certificate:
```{"json" if format == "json" else ""}
{output}
```

This certificate can be verified by anyone using `truthgit verify-proof`.
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error generating proof: {e}")]


async def _verify_proof(certificate: str) -> list[TextContent]:
    """Verify a proof certificate."""
    try:
        from .proof import verify_proof_standalone

        is_valid, message, cert = verify_proof_standalone(certificate)

        if cert:
            text = f"""## Proof Verification

**Claim:** {cert.claim_content}
**Domain:** {cert.claim_domain}
**Consensus:** {round(cert.consensus_value * 100)}%
**Validators:** {", ".join(cert.validators)}
**Timestamp:** {cert.timestamp}
**Repo ID:** {cert.repo_id}

### Result: {"VALID" if is_valid else "INVALID"}
{message}
"""
        else:
            text = f"## Proof Verification Failed\n\n{message}"

        return [TextContent(type="text", text=text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error verifying proof: {e}")]


async def _search_claims(
    query: str, domain: str | None, limit: int, repo_path: Path
) -> list[TextContent]:
    """Search for verified claims."""
    try:
        from .objects import ObjectType
        from .repository import TruthRepository

        repo = TruthRepository(str(repo_path))
        if not repo.is_initialized():
            return [
                TextContent(
                    type="text",
                    text="No TruthGit repository found. Run truthgit init first.",
                )
            ]

        # Search claims
        results = []
        query_lower = query.lower()

        for claim in repo.iter_objects(ObjectType.CLAIM):
            data = json.loads(claim.serialize())
            content = data.get("content", "")
            claim_domain = data.get("domain", "")

            if query_lower in content.lower():
                if domain is None or claim_domain == domain:
                    results.append(
                        {
                            "hash": claim.compute_hash()[:8],
                            "content": content,
                            "domain": claim_domain,
                            "confidence": data.get("confidence", 0),
                        }
                    )

                    if len(results) >= limit:
                        break

        if not results:
            text = f"No claims found matching '{query}'"
        else:
            text = f"## Search Results for '{query}'\n\n"
            for r in results:
                text += f"- **[{r['hash']}]** ({r['domain']}) {r['content'][:80]}...\n"
            text += f"\n*Found {len(results)} result(s)*"

        return [TextContent(type="text", text=text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error searching: {e}")]


async def _get_status(repo_path: Path) -> list[TextContent]:
    """Get repository status."""
    try:
        from .repository import TruthRepository

        repo = TruthRepository(str(repo_path))

        if not repo.is_initialized():
            msg = "No TruthGit repository found.\n\nRun `truthgit init` first."
            return [TextContent(type="text", text=msg)]

        status = repo.status()
        counts = repo.count_objects()

        text = f"""## TruthGit Status

**Repository:** {repo_path}
**Staged claims:** {len(status.get("staged", []))}

### Objects:
- Claims: {counts.get("claim", 0)}
- Verifications: {counts.get("verification", 0)}
- Axioms: {counts.get("axiom", 0)}
- Contexts: {counts.get("context", 0)}
"""

        if status.get("head"):
            text += f"\n**HEAD:** {status['head'][:8]}"

        return [TextContent(type="text", text=text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error getting status: {e}")]


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run():
    """Entry point for the MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
