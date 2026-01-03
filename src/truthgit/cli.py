"""
TruthGit CLI - Command-line interface for truth version control.

Usage:
    truthgit init                    Initialize a new truth repository
    truthgit claim "..." --domain x  Create a new claim
    truthgit verify                  Verify pending claims
    truthgit log                     Show verification history
    truthgit status                  Show repository status
"""

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import TruthRepository, __version__
from .objects import ObjectType, Verification
from .ontological_classifier import ConsensusStatus, DisagreementType

app = typer.Typer(
    name="truthgit",
    help="Version control for verified truth.",
    no_args_is_help=True,
)
console = Console()


def get_repo(path: str = ".truth") -> TruthRepository:
    """Get repository instance."""
    return TruthRepository(path)


def _display_verification_result(verification: Verification, simple_mode: bool = False) -> None:
    """Display verification result with ontological awareness."""
    consensus = verification.consensus
    ontological = getattr(verification, "ontological_consensus", None)

    # Simple mode or no ontological data: use legacy display
    if simple_mode or ontological is None:
        status = "[green]✓ PASSED[/green]" if consensus.passed else "[red]✗ FAILED[/red]"
        rprint(f"\n{status} Consensus: {consensus.value:.0%}")
        rprint(f"Verification: [bold]{verification.short_hash}[/bold]")
        if consensus.passed:
            rprint("\n[green]Claims verified and stored as truth.[/green]")
        else:
            rprint("\n[yellow]Claims did not reach consensus threshold.[/yellow]")
        return

    # Ontological mode: rich display based on status
    rprint("")  # Spacing

    if ontological.status == ConsensusStatus.PASSED:
        rprint("[green]✓ PASSED[/green]")
        rprint(f"  Consensus: {ontological.value:.0%}")
        if ontological.excluded_validators:
            rprint(f"  [dim]Excluded (outlier): {', '.join(ontological.excluded_validators)}[/dim]")
        rprint(f"  Verification: [bold]{verification.short_hash}[/bold]")
        rprint("\n[green]Claims verified and stored as truth.[/green]")

    elif ontological.status == ConsensusStatus.FAILED:
        rprint("[red]✗ FAILED[/red]")
        rprint(f"  Consensus: {ontological.value:.0%} (threshold: {ontological.threshold:.0%})")
        rprint(f"  Verification: [bold]{verification.short_hash}[/bold]")
        rprint("\n[yellow]Claims did not reach consensus threshold.[/yellow]")

    elif ontological.status == ConsensusStatus.UNRESOLVABLE:
        rprint("[bold magenta]⚡ UNRESOLVABLE[/bold magenta] (MYSTERY)")
        rprint("  This disagreement is [bold]philosophically legitimate[/bold]")
        rprint(f"  Average confidence: {ontological.value:.0%}")
        rprint("")
        rprint("  [bold]Preserved positions:[/bold]")
        if ontological.preserved_positions:
            for validator, reasoning in ontological.preserved_positions.items():
                # Truncate long reasonings
                short_reasoning = reasoning[:60] + "..." if len(reasoning) > 60 else reasoning
                rprint(f"    [cyan]{validator}[/cyan]: {short_reasoning}")
        rprint("")
        rprint(f"  Verification: [bold]{verification.short_hash}[/bold]")
        rprint("\n[magenta]→ Disagreement preserved as valuable data[/magenta]")

    elif ontological.status == ConsensusStatus.PENDING_MEDIATION:
        rprint("[bold yellow]⏳ PENDING_MEDIATION[/bold yellow] (GAP)")
        rprint("  This claim requires [bold]human judgment[/bold]")
        rprint(f"  Average confidence: {ontological.value:.0%}")
        rprint("")
        if ontological.mediation_context:
            # Show a brief excerpt
            lines = ontological.mediation_context.split("\n")[:5]
            for line in lines:
                rprint(f"  [dim]{line}[/dim]")
        rprint("")
        rprint(f"  Verification: [bold]{verification.short_hash}[/bold]")
        rprint(f"\n[yellow]→ Run: truthgit mediate {verification.short_hash} to resolve[/yellow]")

    # Show disagreement type if detected
    if ontological.disagreement_type:
        dtype = ontological.disagreement_type
        if dtype == DisagreementType.LOGICAL_ERROR:
            rprint("\n[dim]Disagreement type: LOGICAL_ERROR (validator issue)[/dim]")
        elif dtype == DisagreementType.MYSTERY:
            rprint("\n[dim]Disagreement type: MYSTERY (legitimate unknowable)[/dim]")
        elif dtype == DisagreementType.GAP:
            rprint("\n[dim]Disagreement type: GAP (requires human mediation)[/dim]")


@app.command()
def version():
    """Show TruthGit version."""
    rprint(f"[bold]TruthGit[/bold] v{__version__}")
    rprint("https://truthgit.com")


@app.command()
def init(
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
):
    """Initialize a new truth repository."""
    repo = get_repo(path)

    try:
        repo.init(force=force)
        rprint(f"[green]✓[/green] Initialized truth repository in [bold]{path}/[/bold]")
        rprint("\nNext steps:")
        rprint('  truthgit claim "Your statement here" --domain general')
        rprint("  truthgit verify")
    except FileExistsError:
        rprint(f"[red]✗[/red] Repository already exists at {path}/")
        rprint("  Use --force to reinitialize")
        raise typer.Exit(1)


@app.command()
def status(
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Show repository status."""
    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository")
        rprint("  Run: truthgit init")
        raise typer.Exit(1)

    st = repo.status()

    # Header
    rprint(Panel.fit("[bold]TruthGit Status[/bold]", border_style="blue"))

    # Staged claims
    if st["staged"]:
        rprint(f"\n[yellow]Staged claims ({len(st['staged'])}):[/yellow]")
        for item in st["staged"]:
            rprint(f"  • {item['hash'][:8]} ({item['type']})")
    else:
        rprint("\n[dim]No claims staged[/dim]")

    # HEAD
    if st["head"]:
        rprint(f"\n[green]HEAD:[/green] {st['head'][:8]}")

    # Consensus
    if st["consensus"]:
        rprint(f"[green]Consensus:[/green] {st['consensus'][:8]}")

    # Perspectives
    if st["perspectives"]:
        rprint("\n[blue]Perspectives:[/blue]")
        for name, hash_val in st["perspectives"].items():
            rprint(f"  • {name}: {hash_val[:8]}")


@app.command()
def claim(
    content: str = typer.Argument(..., help="The claim to verify"),
    domain: str = typer.Option("general", "--domain", "-d", help="Knowledge domain"),
    confidence: float = typer.Option(0.5, "--confidence", "-c", help="Initial confidence"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Create a new claim to be verified."""
    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    cl = repo.claim(
        content=content,
        confidence=confidence,
        domain=domain,
    )

    rprint(f"[green]✓[/green] Created claim: [bold]{cl.short_hash}[/bold]")
    rprint(f"  Content: {content[:60]}{'...' if len(content) > 60 else ''}")
    rprint(f"  Domain: {domain}")
    rprint("\nRun [bold]truthgit verify[/bold] to validate with consensus")


@app.command()
def verify(
    local: bool = typer.Option(False, "--local", "-l", help="Use only local validators (Ollama)"),
    simple: bool = typer.Option(
        False, "--simple", "-s", help="Use simple threshold (skip ontological analysis)"
    ),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Verify staged claims with multi-validator consensus.

    By default, uses ontological consensus that understands the NATURE of disagreement:
    - LOGICAL_ERROR: One validator has a bug (excluded, recalculated)
    - MYSTERY: Legitimate philosophical disagreement (preserved as data)
    - GAP: Requires human mediation (escalated)

    Use --simple for legacy threshold-based consensus.
    """
    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    staged = repo.get_staged()
    if not staged:
        rprint("[yellow]Nothing to verify[/yellow]")
        rprint('  Create a claim first: truthgit claim "..."')
        raise typer.Exit(0)

    rprint(f"[bold]Verifying {len(staged)} claim(s)...[/bold]\n")

    # Get validators
    from .validators import get_default_validators, validate_claim

    try:
        validators = get_default_validators(local_only=local)
    except Exception as e:
        rprint(f"[red]✗[/red] Could not find validators: {e}")
        rprint("\nTo use local validation, install Ollama:")
        rprint("  https://ollama.ai")
        rprint("  ollama pull llama3")
        raise typer.Exit(1)

    if len(validators) < 2:
        rprint("[red]✗[/red] Need at least 2 validators")
        if local:
            rprint("  Try: ollama pull llama3 && ollama pull mistral")
        else:
            rprint("  Set API keys or use --local with Ollama")
        raise typer.Exit(1)

    rprint(f"Using validators: {', '.join(v.name for v in validators)}\n")

    # Validate each claim
    all_results = {}
    for item in staged:
        claim_obj = repo.load(ObjectType.CLAIM, item["hash"])
        if not claim_obj:
            continue

        rprint(f"[dim]Validating:[/dim] {claim_obj.content[:50]}...")

        results, avg = validate_claim(
            claim=claim_obj.content,
            domain=claim_obj.domain,
            validators=validators,
        )

        for r in results:
            if r.success:
                all_results[r.validator_name] = (r.confidence, r.reasoning)
                rprint(f"  [{r.validator_name}] {r.confidence:.0%} - {r.reasoning[:40]}...")
            else:
                rprint(f"  [{r.validator_name}] [red]Error:[/red] {r.error}")

    # Create verification
    if all_results:
        # Get claim content for ontological analysis
        claim_content = ""
        claim_domain = "general"
        for item in staged:
            claim_obj = repo.load(ObjectType.CLAIM, item["hash"])
            if claim_obj:
                claim_content = claim_obj.content
                claim_domain = claim_obj.domain
                break

        verification = repo.verify(
            verifier_results=all_results,
            trigger="cli",
            use_ontological=not simple,
            claim_content=claim_content,
            claim_domain=claim_domain,
        )

        if verification:
            _display_verification_result(verification, simple)
    else:
        rprint("\n[red]✗[/red] No successful validations")


@app.command()
def log(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of entries"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Show verification history."""
    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    history = repo.history(limit=limit)

    if not history:
        rprint("[dim]No verifications yet[/dim]")
        return

    table = Table(title="Truth Log")
    table.add_column("Hash", style="cyan")
    table.add_column("Consensus", justify="right")
    table.add_column("Status")
    table.add_column("Timestamp")

    for v in history:
        status = "[green]✓[/green]" if v.consensus.passed else "[red]✗[/red]"
        table.add_row(
            v.short_hash,
            f"{v.consensus.value:.0%}",
            status,
            v.timestamp[:19],
        )

    console.print(table)


@app.command("cat")
def cat_object(
    hash_prefix: str = typer.Argument(..., help="Object hash (or prefix)"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Show details of a truth object."""
    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository")
        raise typer.Exit(1)

    # Try to find object by prefix
    for obj_type in ObjectType:
        for obj in repo.iter_objects(obj_type):
            if obj.hash.startswith(hash_prefix):
                rprint(
                    Panel.fit(
                        f"[bold]{obj_type.value.upper()}[/bold] {obj.short_hash}",
                        border_style="blue",
                    )
                )
                rprint(obj.serialize())
                return

    rprint(f"[red]✗[/red] Object not found: {hash_prefix}")
    raise typer.Exit(1)


@app.command()
def validators(
    local: bool = typer.Option(False, "--local", "-l", help="Show only local"),
):
    """Show available validators."""
    from .validators import (
        ClaudeValidator,
        GeminiValidator,
        GPTValidator,
        HuggingFaceValidator,
        OllamaValidator,
    )

    table = Table(title="Available Validators")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")

    # Local
    ollama = OllamaValidator("llama3")
    status = "[green]Ready[/green]" if ollama.is_available() else "[red]Not running[/red]"
    table.add_row("OLLAMA", "Local", status)

    if not local:
        # Cloud
        for name, validator_cls in [
            ("CLAUDE", ClaudeValidator),
            ("GPT", GPTValidator),
            ("GEMINI", GeminiValidator),
            ("HUGGINGFACE", HuggingFaceValidator),
        ]:
            v = validator_cls()
            status = "[green]Ready[/green]" if v.is_available() else "[dim]No API key[/dim]"
            table.add_row(name, "Cloud", status)

    console.print(table)

    rprint("\n[bold]Local setup:[/bold]")
    rprint("  1. Install Ollama: https://ollama.ai")
    rprint("  2. Pull a model: ollama pull llama3")
    rprint("\n[bold]Cloud setup:[/bold] (optional)")
    rprint("  ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, HF_TOKEN")


# =============================================================================
# KNOWLEDGE EXTRACTION COMMANDS
# =============================================================================


@app.command()
def extract(
    source: str = typer.Argument(..., help="Text or file path to extract from"),
    domain: str = typer.Option("general", "--domain", "-d", help="Knowledge domain"),
    auto_verify: bool = typer.Option(False, "--verify", "-v", help="Auto-verify claims"),
    local: bool = typer.Option(True, "--local", "-l", help="Use local LLM (Ollama)"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Extract atomic claims from a document or text."""
    import os

    from .extractor import KnowledgeExtractor

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    # Check if source is a file
    if os.path.isfile(source):
        with open(source, encoding="utf-8") as f:
            text = f.read()
        rprint(f"[dim]Reading from file:[/dim] {source}")
    else:
        text = source

    rprint(f"[bold]Extracting claims from {len(text)} characters...[/bold]\n")

    try:
        extractor = KnowledgeExtractor(repo, use_local=local)
        claims = extractor.ingest_document(
            document=text,
            domain=domain,
            auto_verify=auto_verify,
        )
    except Exception as e:
        rprint(f"[red]✗[/red] Extraction failed: {e}")
        if local:
            rprint("\nMake sure Ollama is running: ollama serve")
        raise typer.Exit(1)

    if not claims:
        rprint("[yellow]No claims extracted[/yellow]")
        return

    rprint(f"[green]✓[/green] Extracted {len(claims)} claims:\n")

    table = Table(title=f"Claims ({domain})")
    table.add_column("Hash", style="cyan", width=10)
    table.add_column("Content", width=50)
    table.add_column("Confidence", justify="right", width=10)

    for claim in claims:
        table.add_row(
            claim.short_hash,
            claim.content[:50] + ("..." if len(claim.content) > 50 else ""),
            f"{claim.confidence:.0%}",
        )

    console.print(table)

    rprint("\n[dim]Claims staged. Run [bold]truthgit verify[/bold] to validate.[/dim]")


@app.command()
def patterns(
    domain: str = typer.Option(None, "--domain", "-d", help="Filter by domain"),
    min_confidence: float = typer.Option(0.6, "--min", "-m", help="Min confidence"),
    local: bool = typer.Option(True, "--local", "-l", help="Use local LLM"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Find patterns across verified claims."""
    from .extractor import KnowledgeExtractor

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    rprint("[bold]Analyzing patterns...[/bold]\n")

    try:
        extractor = KnowledgeExtractor(repo, use_local=local)
        found_patterns = extractor.find_patterns(
            domain=domain,
            min_confidence=min_confidence,
        )
    except Exception as e:
        rprint(f"[red]✗[/red] Pattern analysis failed: {e}")
        raise typer.Exit(1)

    if not found_patterns:
        rprint("[yellow]No patterns found[/yellow]")
        rprint("  Extract more claims first: truthgit extract '...'")
        return

    table = Table(title="Detected Patterns")
    table.add_column("Type", style="blue", width=15)
    table.add_column("Description", width=40)
    table.add_column("Claims", width=20)
    table.add_column("Confidence", justify="right", width=10)

    for p in found_patterns:
        claims_str = ", ".join(h[:8] for h in p.claims)
        table.add_row(
            p.pattern_type.value,
            p.description[:40] + ("..." if len(p.description) > 40 else ""),
            claims_str,
            f"{p.confidence:.0%}",
        )

    console.print(table)


@app.command()
def contradictions(
    claim_hash: str = typer.Argument(None, help="Check specific claim (optional)"),
    local: bool = typer.Option(True, "--local", "-l", help="Use local LLM"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Detect contradictions between claims."""
    from .extractor import KnowledgeExtractor

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    extractor = KnowledgeExtractor(repo, use_local=local)

    # Get claims to check
    claims = list(repo.iter_objects(ObjectType.CLAIM))

    if not claims:
        rprint("[yellow]No claims to check[/yellow]")
        return

    if claim_hash:
        # Check specific claim
        target = None
        for c in claims:
            if c.hash.startswith(claim_hash):
                target = c
                break
        if not target:
            rprint(f"[red]✗[/red] Claim not found: {claim_hash}")
            raise typer.Exit(1)

        rprint(f"[bold]Checking contradictions for:[/bold] {target.content[:50]}...\n")
        found = extractor.detect_contradictions(target, against=claims)
    else:
        # Check all claims against each other
        rprint(f"[bold]Checking {len(claims)} claims for contradictions...[/bold]\n")
        found = []
        seen = set()
        for c in claims:
            for contradiction in extractor.detect_contradictions(c, against=claims):
                # Avoid duplicates
                key = tuple(sorted([contradiction.claim_a_hash, contradiction.claim_b_hash]))
                if key not in seen:
                    seen.add(key)
                    found.append(contradiction)

    if not found:
        rprint("[green]✓[/green] No contradictions found")
        return

    table = Table(title="Detected Contradictions")
    table.add_column("Severity", style="red", width=10)
    table.add_column("Claim A", width=15)
    table.add_column("Claim B", width=15)
    table.add_column("Explanation", width=35)
    table.add_column("Confidence", justify="right", width=10)

    for c in found:
        table.add_row(
            c.severity.value.upper(),
            c.claim_a_hash[:12],
            c.claim_b_hash[:12],
            c.explanation[:35] + ("..." if len(c.explanation) > 35 else ""),
            f"{c.confidence:.0%}",
        )

    console.print(table)

    if any(c.resolution_hint for c in found):
        rprint("\n[bold]Resolution hints:[/bold]")
        for c in found:
            if c.resolution_hint:
                rprint(f"  • {c.claim_a_hash[:8]}↔{c.claim_b_hash[:8]}: {c.resolution_hint}")


@app.command()
def axioms(
    promote: bool = typer.Option(False, "--promote", help="Promote eligible claims"),
    min_verifications: int = typer.Option(2, "--min-verifications", "-n"),
    min_confidence: float = typer.Option(0.90, "--min-confidence", "-c"),
    local: bool = typer.Option(True, "--local", "-l", help="Use local LLM"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Show axiom candidates and optionally promote them."""
    from .extractor import KnowledgeExtractor

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    # Show existing axioms
    existing = list(repo.iter_objects(ObjectType.AXIOM))
    if existing:
        table = Table(title="Existing Axioms")
        table.add_column("Hash", style="cyan", width=10)
        table.add_column("Content", width=50)
        table.add_column("Type", width=15)
        table.add_column("Domain", width=10)

        for a in existing:
            table.add_row(
                a.short_hash,
                a.content[:50] + ("..." if len(a.content) > 50 else ""),
                a.axiom_type.value,
                a.domain,
            )

        console.print(table)
        rprint("")

    # Find candidates
    extractor = KnowledgeExtractor(repo, use_local=local)
    candidates = extractor.find_axiom_candidates(
        min_verifications=min_verifications,
        min_avg_confidence=min_confidence,
    )

    if not candidates:
        rprint("[dim]No axiom candidates found[/dim]")
        rprint(f"  Requires: {min_verifications}+ verifications, ")
        rprint(f"  {min_confidence:.0%}+ avg confidence")
        return

    table = Table(title="Axiom Candidates")
    table.add_column("Hash", style="yellow", width=10)
    table.add_column("Content", width=40)
    table.add_column("Verifications", justify="right", width=12)
    table.add_column("Avg Confidence", justify="right", width=12)

    for claim, avg_conf, num_verifications in candidates:
        table.add_row(
            claim.short_hash,
            claim.content[:40] + ("..." if len(claim.content) > 40 else ""),
            str(num_verifications),
            f"{avg_conf:.1%}",
        )

    console.print(table)

    if promote:
        rprint("\n[bold]Promoting to axioms...[/bold]")
        promoted = 0
        for claim, avg_conf, _ in candidates:
            axiom = extractor.promote_to_axiom(
                claim,
                min_verifications=min_verifications,
                min_avg_confidence=min_confidence,
            )
            if axiom:
                rprint(f"  [green]✓[/green] {claim.short_hash} → AXIOM {axiom.short_hash}")
                promoted += 1
            else:
                rprint(f"  [yellow]○[/yellow] {claim.short_hash} has contradictions, skipped")

        rprint(f"\n[green]Promoted {promoted} claims to axioms[/green]")


@app.command()
def graph(
    domain: str = typer.Argument(..., help="Domain to export"),
    output: str = typer.Option(None, "--output", "-o", help="Output file (JSON)"),
    local: bool = typer.Option(True, "--local", "-l", help="Use local LLM"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Export knowledge graph for a domain."""
    import json as json_module

    from .extractor import KnowledgeExtractor

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    rprint(f"[bold]Building knowledge graph for: {domain}[/bold]\n")

    extractor = KnowledgeExtractor(repo, use_local=local)
    graph_data = extractor.extract_domain_graph(domain)

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    rprint("[green]✓[/green] Graph extracted:")
    rprint(f"  Nodes: {len(nodes)} ({sum(1 for n in nodes if n['type'] == 'axiom')} axioms)")
    rprint(f"  Edges: {len(edges)} patterns")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json_module.dump(graph_data, f, indent=2)
        rprint(f"\n[dim]Saved to: {output}[/dim]")
    else:
        # Print summary
        if nodes:
            rprint("\n[bold]Nodes:[/bold]")
            for n in nodes[:10]:
                icon = "★" if n["type"] == "axiom" else "○"
                rprint(f"  {icon} [{n['short_hash']}] {n['content'][:40]}...")

            if len(nodes) > 10:
                rprint(f"  ... and {len(nodes) - 10} more")

        if edges:
            rprint("\n[bold]Edges:[/bold]")
            for e in edges[:10]:
                rprint(f"  {e['source'][:8]} ─[{e['type']}]─▶ {e['target'][:8]}")

            if len(edges) > 10:
                rprint(f"  ... and {len(edges) - 10} more")


# =============================================================================
# DOCUMENTATION SYNC COMMANDS
# =============================================================================


@app.command()
def sync(
    paths: list[str] = typer.Argument(None, help="Paths to sync (dirs or files)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-sync all"),
    verify: bool = typer.Option(False, "--verify", "-v", help="Auto-verify claims"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for changes"),
    local: bool = typer.Option(True, "--local", "-l", help="Use local LLM"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Watch interval"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Sync documentation with TruthGit."""
    from .sync import DocumentSync

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository. Run: truthgit init")
        raise typer.Exit(1)

    doc_sync = DocumentSync(repo, use_local=local)

    # If no paths, use previously watched or current dir
    if not paths:
        if doc_sync.state.watch_paths:
            paths = doc_sync.state.watch_paths
            rprint(f"[dim]Using saved watch paths: {paths}[/dim]\n")
        else:
            paths = ["."]
            rprint("[dim]No paths specified, using current directory[/dim]\n")

    if watch:
        # Watch mode
        rprint(f"[bold]Watching {len(paths)} path(s) for changes...[/bold]")
        rprint("[dim]Press Ctrl+C to stop[/dim]\n")

        def on_change(result):
            rprint(
                f"[green]✓[/green] Synced: {result.files_new} new, "
                f"{result.files_changed} changed, "
                f"{result.claims_extracted} claims extracted"
            )
            if result.errors:
                for err in result.errors:
                    rprint(f"  [red]Error:[/red] {err}")

        try:
            doc_sync.watch(
                paths=paths,
                interval=interval,
                auto_verify=verify,
                on_change=on_change,
            )
        except KeyboardInterrupt:
            rprint("\n[dim]Stopped watching[/dim]")
    else:
        # One-time sync
        rprint(f"[bold]Syncing {len(paths)} path(s)...[/bold]\n")

        def on_progress(msg, current, total):
            rprint(f"  [{current}/{total}] {msg}")

        result = doc_sync.sync(
            paths=paths,
            force=force,
            auto_verify=verify,
            on_progress=on_progress,
        )

        # Summary
        rprint("\n[green]✓[/green] Sync complete:")
        rprint(f"  Files scanned:  {result.files_scanned}")
        rprint(f"  New files:      {result.files_new}")
        rprint(f"  Changed files:  {result.files_changed}")
        rprint(f"  Deleted files:  {result.files_deleted}")
        rprint(f"  Claims extracted: {result.claims_extracted}")

        if result.errors:
            rprint(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
            for err in result.errors[:5]:
                rprint(f"  • {err}")
            if len(result.errors) > 5:
                rprint(f"  ... and {len(result.errors) - 5} more")

        if result.claims_extracted > 0:
            rprint("\n[dim]Run [bold]truthgit verify[/bold] to validate claims[/dim]")


@app.command("sync-status")
def sync_status(
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Show documentation sync status."""
    from .sync import DocumentSync

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository")
        raise typer.Exit(1)

    doc_sync = DocumentSync(repo)
    st = doc_sync.status()

    rprint(Panel.fit("[bold]Sync Status[/bold]", border_style="blue"))

    if st["last_full_sync"]:
        rprint(f"\n[green]Last sync:[/green] {st['last_full_sync'][:19]}")
    else:
        rprint("\n[yellow]Never synced[/yellow]")

    rprint(f"[blue]Files tracked:[/blue] {st['files_tracked']}")
    rprint(f"[blue]Total claims:[/blue] {st['total_claims']}")

    if st["watch_paths"]:
        rprint("\n[bold]Watch paths:[/bold]")
        for p in st["watch_paths"]:
            rprint(f"  • {p}")

    if st["domains"]:
        rprint("\n[bold]Domains:[/bold]")
        for d in st["domains"]:
            rprint(f"  • {d}")


@app.command("sync-diff")
def sync_diff(
    paths: list[str] = typer.Argument(None, help="Paths to check"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Show what would change on next sync."""
    from .sync import DocumentSync

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository")
        raise typer.Exit(1)

    doc_sync = DocumentSync(repo)

    if not paths:
        paths = doc_sync.state.watch_paths or ["."]

    diff = doc_sync.diff(paths)

    if not any([diff["new"], diff["changed"], diff["deleted"]]):
        rprint("[green]✓[/green] Everything up to date")
        return

    if diff["new"]:
        rprint(f"\n[green]New files ({len(diff['new'])}):[/green]")
        for f in diff["new"][:10]:
            rprint(f"  + {f}")
        if len(diff["new"]) > 10:
            rprint(f"  ... and {len(diff['new']) - 10} more")

    if diff["changed"]:
        rprint(f"\n[yellow]Changed files ({len(diff['changed'])}):[/yellow]")
        for f in diff["changed"][:10]:
            rprint(f"  ~ {f}")
        if len(diff["changed"]) > 10:
            rprint(f"  ... and {len(diff['changed']) - 10} more")

    if diff["deleted"]:
        rprint(f"\n[red]Deleted files ({len(diff['deleted'])}):[/red]")
        for f in diff["deleted"][:10]:
            rprint(f"  - {f}")
        if len(diff["deleted"]) > 10:
            rprint(f"  ... and {len(diff['deleted']) - 10} more")

    rprint("\n[dim]Run [bold]truthgit sync[/bold] to apply changes[/dim]")


@app.command("sync-domain")
def sync_domain(
    pattern: str = typer.Argument(..., help="Path pattern to match"),
    domain: str = typer.Argument(..., help="Domain to assign"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Set domain mapping for paths matching a pattern."""
    from .sync import DocumentSync

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository")
        raise typer.Exit(1)

    doc_sync = DocumentSync(repo)
    doc_sync.set_domain_mapping(pattern, domain)

    rprint(f"[green]✓[/green] Set mapping: '{pattern}' → domain '{domain}'")


# =============================================================================
# PROOF COMMANDS
# =============================================================================


@app.command()
def prove(
    hash_prefix: str = typer.Argument(..., help="Hash of claim or verification to prove"),
    output: str = typer.Option(None, "--output", "-o", help="Output file for certificate"),
    compact: bool = typer.Option(False, "--compact", "-c", help="Output compact base64 format"),
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """
    Generate a cryptographic proof certificate for a verified claim.

    The certificate can be shared and verified by anyone without
    access to the original repository.

    Examples:
        truthgit prove d745672a                    # Print JSON certificate
        truthgit prove d745672a -o proof.json      # Save to file
        truthgit prove d745672a --compact          # Compact base64 format
    """
    from .proof import ProofManager

    repo = get_repo(path)

    if not repo.is_initialized():
        rprint("[red]✗[/red] Not a truth repository")
        raise typer.Exit(1)

    # Find the object
    obj = repo.get_object_by_prefix(hash_prefix)
    if not obj:
        rprint(f"[red]✗[/red] No object found with prefix: {hash_prefix}")
        raise typer.Exit(1)

    obj_type, obj_data = obj

    # Determine claim and verification
    if obj_type.value == "claim":
        # Find the verification that includes this claim
        claim_hash = obj_data.get("$hash", "")
        claim_content = obj_data.get("content", "")
        claim_domain = obj_data.get("domain", "general")

        # Look for verification containing this claim
        verifications = repo.find_verifications_for_claim(claim_hash)
        if not verifications:
            rprint(f"[red]✗[/red] Claim {hash_prefix} has not been verified yet")
            rprint("  Run: truthgit verify")
            raise typer.Exit(1)

        # Use most recent verification
        verification = verifications[-1]
        verification_hash = verification.get("$hash", "")
        consensus = verification.get("consensus", {})

    elif obj_type.value == "verification":
        verification = obj_data
        verification_hash = obj_data.get("$hash", "")
        consensus = obj_data.get("consensus", {})

        # Get claim from context
        context_hash = verification.get("context", "")
        context = repo.get_object(ObjectType.CONTEXT, context_hash)
        if not context:
            rprint("[red]✗[/red] Could not find context for verification")
            raise typer.Exit(1)

        claims = context.get("claims", [])
        if not claims:
            rprint("[red]✗[/red] Verification has no claims")
            raise typer.Exit(1)

        # Get first claim - claims can be strings or dicts with 'hash' key
        first_claim = claims[0]
        claim_hash = first_claim["hash"] if isinstance(first_claim, dict) else first_claim

        claim_obj = repo.get_object(ObjectType.CLAIM, claim_hash)
        if not claim_obj:
            rprint("[red]✗[/red] Could not find claim")
            raise typer.Exit(1)

        claim_content = claim_obj.get("content", "")
        claim_domain = claim_obj.get("domain", "general")
    else:
        rprint(f"[red]✗[/red] Cannot prove object of type: {obj_type.value}")
        rprint("  Only claims and verifications can be proven")
        raise typer.Exit(1)

    # Create proof
    proof_manager = ProofManager(repo.root)

    try:
        cert = proof_manager.create_proof(
            claim_hash=claim_hash,
            claim_content=claim_content,
            claim_domain=claim_domain,
            verification_hash=verification_hash,
            consensus_value=consensus.get("value", 0),
            consensus_passed=consensus.get("passed", False),
            validators=list(verification.get("verifiers", {}).keys()),
            timestamp=verification.get("metadata", {}).get("timestamp"),
        )
    except FileNotFoundError:
        rprint("[red]✗[/red] No proof keys found. Reinitialize with: truthgit init --force")
        raise typer.Exit(1)

    # Output
    if compact:
        result = cert.to_compact()
    else:
        result = cert.to_json()

    if output:
        from pathlib import Path

        Path(output).write_text(result)
        rprint(f"[green]✓[/green] Proof certificate saved to: {output}")
        rprint(f"  Repo ID: {cert.repo_id}")
        rprint(f"  Claim: {cert.claim_content[:50]}...")
        rprint(f"  Consensus: {cert.consensus_value:.0%}")
    else:
        rprint(Panel.fit("[bold]Proof Certificate[/bold]", border_style="green"))
        rprint(result)

    hint = "<file>" if output else "<certificate>"
    rprint(f"\n[dim]Verify with: truthgit verify-proof {hint}[/dim]")


@app.command("verify-proof")
def verify_proof_cmd(
    certificate: str = typer.Argument(..., help="Certificate (file path, JSON, or compact string)"),
):
    """
    Verify a proof certificate.

    Works without access to the original repository - anyone can verify.

    Examples:
        truthgit verify-proof proof.json           # Verify from file
        truthgit verify-proof '{"version":...}'    # Verify JSON string
        truthgit verify-proof eyJ2ZXJzaW9...       # Verify compact format
    """
    from pathlib import Path

    from .proof import verify_proof_standalone

    # Determine input type
    # If it looks like JSON or base64, treat as data directly
    if certificate.startswith("{") or certificate.startswith("eyJ"):
        cert_data = certificate
    else:
        cert_path = Path(certificate)
        if cert_path.exists():
            cert_data = cert_path.read_text()
        else:
            cert_data = certificate

    # Verify
    is_valid, message, cert = verify_proof_standalone(cert_data)

    if cert:
        rprint(Panel.fit("[bold]Proof Verification[/bold]", border_style="blue"))
        rprint(f"\n[bold]Claim:[/bold] {cert.claim_content}")
        rprint(f"[bold]Domain:[/bold] {cert.claim_domain}")
        rprint(f"[bold]Consensus:[/bold] {cert.consensus_value:.0%}")
        rprint(f"[bold]Validators:[/bold] {', '.join(cert.validators)}")
        rprint(f"[bold]Timestamp:[/bold] {cert.timestamp}")
        rprint(f"[bold]Repo ID:[/bold] {cert.repo_id}")

    if is_valid:
        rprint(f"\n[green]✓ VALID[/green] {message}")
    else:
        rprint(f"\n[red]✗ INVALID[/red] {message}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
