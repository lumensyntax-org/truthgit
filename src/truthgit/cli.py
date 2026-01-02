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
from .objects import ObjectType

app = typer.Typer(
    name="truthgit",
    help="Version control for verified truth.",
    no_args_is_help=True,
)
console = Console()


def get_repo(path: str = ".truth") -> TruthRepository:
    """Get repository instance."""
    return TruthRepository(path)


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
    path: str = typer.Option(".truth", "--path", "-p", help="Repository path"),
):
    """Verify staged claims with multi-validator consensus."""
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
        verification = repo.verify(
            verifier_results=all_results,
            trigger="cli",
        )

        if verification:
            consensus = verification.consensus

            # Display result
            status = "[green]✓ PASSED[/green]" if consensus.passed else "[red]✗ FAILED[/red]"
            rprint(f"\n{status} Consensus: {consensus.value:.0%}")
            rprint(f"Verification: [bold]{verification.short_hash}[/bold]")

            if consensus.passed:
                rprint("\n[green]Claims verified and stored as truth.[/green]")
            else:
                rprint("\n[yellow]Claims did not reach consensus threshold.[/yellow]")
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
    from .validators import ClaudeValidator, GeminiValidator, GPTValidator, OllamaValidator

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
        ]:
            v = validator_cls()
            status = "[green]Ready[/green]" if v.is_available() else "[dim]No API key[/dim]"
            table.add_row(name, "Cloud", status)

    console.print(table)

    rprint("\n[bold]Local setup:[/bold]")
    rprint("  1. Install Ollama: https://ollama.ai")
    rprint("  2. Pull a model: ollama pull llama3")
    rprint("\n[bold]Cloud setup:[/bold] (optional)")
    rprint("  Set environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY")


if __name__ == "__main__":
    app()
