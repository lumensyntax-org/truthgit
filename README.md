# TruthGit

<div align="center">

**Version control for verified truth.**

[![PyPI](https://img.shields.io/pypi/v/truthgit.svg)](https://pypi.org/project/truthgit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

[Website](https://truthgit.com) • [Documentation](https://truthgit.com/docs) • [Discord](https://discord.gg/truthgit)

</div>

---

Like Git tracks code, **TruthGit** tracks claims. Verify with AI consensus. Store immutably. Trust, but verify.

```bash
$ truthgit init
$ truthgit claim "Water boils at 100°C at sea level" --domain physics
$ truthgit verify

[OLLAMA:HERMES3] 95% - Accurate under standard atmospheric pressure
[OLLAMA:NEMOTRON] 94% - True at 1 atm, varies with altitude

✓ PASSED  Consensus: 95%
Verification: a7f3b2c1
```

### What makes TruthGit different?

TruthGit doesn't just count votes—it understands the **nature** of disagreement:

```bash
$ truthgit claim "Free will exists" --domain philosophy
$ truthgit verify

[OLLAMA:HERMES3] 30% - Contested philosophical question
[OLLAMA:NEMOTRON] 30% - Determinism vs libertarianism debate

⚡ UNRESOLVABLE  Type: MYSTERY
Preserved positions: 2

# Not a failure—preserved as legitimate philosophical disagreement
```

## Why TruthGit?

In a world of AI-generated content, misinformation, and information overload, we need **infrastructure for verified truth**.

TruthGit provides:
- **Ontological consensus** — Understands *what type* of disagreement, not just *how much*
- **Immutable storage** — Claims are stored by their content hash (like Git)
- **Multi-validator consensus** — No single AI is trusted alone
- **Fallacy detection** — Identifies logical errors in validator reasoning
- **Auditable history** — Every verification is traceable
- **Local-first** — Works offline with Ollama, no API keys required
- **Open protocol** — Self-host, federate, integrate

## Ontological Consensus (v0.5.0)

Most verification systems ask: "How much agreement?" TruthGit asks: **"What type of disagreement?"**

### The Three Types

| Type | Symbol | Meaning | Action |
|------|--------|---------|--------|
| **PASSED** | ✓ | Validators agree above threshold | Claim verified |
| **LOGICAL_ERROR** | ✗ | One validator has a bug/fallacy | Exclude outlier, recalculate |
| **MYSTERY** | ⚡ | Legitimate unknowable (philosophy) | Preserve all positions as data |
| **GAP** | ⏳ | Unfalsifiable claim | Escalate to human mediation |

### Why This Matters

```
Traditional: 60% consensus on "Free will exists" → FAILED ❌
TruthGit:    60% consensus on "Free will exists" → MYSTERY ⚡ (preserved)
```

Validators agreeing on uncertainty doesn't resolve underlying unknowability. A contested philosophical claim with high agreement is still a **MYSTERY**—and that's valuable information, not a failure.

### Domain-Aware Processing

For philosophical domains (`philosophy`, `ethics`, `religion`, `metaphysics`, `epistemology`), TruthGit analyzes the **claim's nature first**:

```python
from truthgit.ontological_classifier import calculate_ontological_consensus

results = {
    "CLAUDE": (0.70, "Free will emerges from complexity"),
    "GPT": (0.30, "Determinism is more parsimonious"),
    "GEMINI": (0.50, "The question may be malformed"),
}

consensus = calculate_ontological_consensus(
    claim="Free will exists",
    validator_results=results,
    domain="philosophy"
)

print(consensus.status)           # ConsensusStatus.UNRESOLVABLE
print(consensus.disagreement_type) # DisagreementType.MYSTERY
print(consensus.preserved_positions)  # All 3 reasonings preserved
```

### Fallacy Detection

TruthGit detects logical fallacies in validator reasoning:

```python
from truthgit.fallacy_detector import detect_fallacies

result = detect_fallacies("He's an idiot, so his argument is wrong.")
print(result.valid)      # False
print(result.fallacies)  # [Fallacy(type='AD_HOMINEM', ...)]
```

**Detected fallacies (11 types):**

| Formal | Informal |
|--------|----------|
| Affirming the Consequent | Ad Hominem |
| Denying the Antecedent | Straw Man |
| False Dilemma | Appeal to Authority |
| Circular Reasoning | Slippery Slope |
| | Appeal to Emotion |
| | Hasty Generalization |
| | Red Herring |

When a validator's reasoning contains fallacies, TruthGit classifies the disagreement as `LOGICAL_ERROR` and can exclude the outlier.

### Hypothesis Testing

TruthGit evaluates claims for falsifiability:

```python
from truthgit.hypothesis_tester import evaluate_hypothesis, EpistemicStatus

result = evaluate_hypothesis("Everything happens for a reason")
print(result.status)      # EpistemicStatus.UNFALSIFIABLE
print(result.falsifiable) # False

result = evaluate_hypothesis("Evolution explains biodiversity")
print(result.status)      # EpistemicStatus.ESTABLISHED
print(result.falsifiable) # True
```

**Epistemic statuses:**
- `ESTABLISHED` — Scientific consensus exists
- `CONTESTED` — Active academic debate
- `SPECULATIVE` — Insufficient evidence
- `FRINGE` — Contradicts established science
- `UNFALSIFIABLE` — Cannot be tested

## Installation

```bash
# Install TruthGit
pip install truthgit

# For local validation (recommended)
pip install truthgit[local]

# For cloud APIs (optional)
pip install truthgit[cloud]

# Everything
pip install truthgit[all]
```

### Local Setup (No API Keys)

TruthGit works locally with [Ollama](https://ollama.ai):

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models for diverse validation
ollama pull llama3
ollama pull mistral
ollama pull phi3

# Verify setup
truthgit validators --local
```

## Quick Start

```bash
# Initialize a truth repository
truthgit init

# Create claims to verify
truthgit claim "The Earth orbits the Sun" --domain astronomy
truthgit claim "Python was created by Guido van Rossum" --domain programming

# Verify with local AI consensus
truthgit verify --local

# View verification history
truthgit log
```

## Commands

| Command | Description |
|---------|-------------|
| `truthgit init` | Initialize a new truth repository |
| `truthgit claim "..." --domain x` | Create a claim to verify |
| `truthgit verify [--local]` | Verify with ontological consensus |
| `truthgit verify --simple` | Verify with simple threshold only |
| `truthgit status` | Show repository status |
| `truthgit log` | Show verification history |
| `truthgit cat <hash>` | Show object details |
| `truthgit validators` | Show available validators |

### Verification Modes

```bash
# Default: Ontological consensus (understands disagreement types)
truthgit verify --local

# Simple: Threshold-only (legacy behavior)
truthgit verify --local --simple
```

## How It Works

### 1. Content-Addressable Storage

Every object is stored by its SHA-256 hash (like Git):

```
.truth/
├── objects/
│   ├── cl/  # Claims
│   ├── ax/  # Axioms (immutable truths)
│   ├── ct/  # Contexts (groups of claims)
│   └── vf/  # Verifications (snapshots)
├── refs/
│   ├── consensus/  # Verified truth
│   └── perspectives/  # Per-validator views
└── HEAD
```

### 2. Ontological Consensus

Claims are verified by multiple independent validators, then classified by disagreement type:

```
        ┌─────────────┐
        │   Claim     │
        │  + Domain   │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌───────┐  ┌───────┐  ┌───────┐
│Hermes │  │Nemotron│ │ Phi3  │
│  92%  │  │  88%   │ │  90%  │
└───────┘  └───────┘  └───────┘
               │
               ▼
     ┌─────────────────┐
     │ Ontological     │
     │ Classification  │
     └────────┬────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 PASSED    MYSTERY     GAP
   ✓          ⚡         ⏳
 (verify)  (preserve) (mediate)
```

**Flow:**
1. Analyze claim's epistemic nature (falsifiable? contested?)
2. For philosophy domains: claim nature determines handling
3. For science domains: variance triggers fallacy detection
4. Classify disagreement → take appropriate action

Default threshold: **66%** (configurable)

### 3. Verification as Commit

Like Git commits, verifications are immutable snapshots:

```python
from truthgit import TruthRepository

repo = TruthRepository()
repo.init()

# Create claim
claim = repo.claim(
    content="E=mc²",
    domain="physics",
    confidence=0.9,
)

# Verify with multiple validators (ontological by default)
verification = repo.verify(
    verifier_results={
        "HERMES3": (0.95, "Mass-energy equivalence confirmed"),
        "NEMOTRON": (0.92, "Einstein's famous equation"),
        "PHI3": (0.94, "Verified E=mc² relationship"),
    },
    claim_content="E=mc²",
    claim_domain="physics",
)

print(f"Consensus: {verification.consensus.value:.0%}")
# Consensus: 94%

# Access ontological analysis
if verification.ontological_consensus:
    onto = verification.ontological_consensus
    print(f"Status: {onto.status}")           # PASSED
    print(f"Type: {onto.disagreement_type}")  # None (no disagreement)
```

#### Handling Philosophy Claims

```python
# Philosophy claims are handled differently
claim = repo.claim(
    content="Consciousness is fundamental to reality",
    domain="philosophy",
    confidence=0.5,
)

verification = repo.verify(
    verifier_results={
        "CLAUDE": (0.60, "Panpsychism has merit"),
        "GPT": (0.40, "Emergentism is simpler"),
    },
    claim_content="Consciousness is fundamental to reality",
    claim_domain="philosophy",
)

onto = verification.ontological_consensus
print(onto.status)              # UNRESOLVABLE
print(onto.disagreement_type)   # MYSTERY
print(onto.preserved_positions) # Both reasonings preserved
```

## Validators

TruthGit supports pluggable validators:

### Local (No API Keys)

```python
from truthgit.validators import OllamaValidator

validators = [
    OllamaValidator("llama3"),
    OllamaValidator("mistral"),
    OllamaValidator("phi3"),
]
```

### Cloud (Optional)

```python
from truthgit.validators import ClaudeValidator, GPTValidator, GeminiValidator

# Set environment variables:
# ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY

validators = [
    ClaudeValidator(),
    GPTValidator(),
    GeminiValidator(),
]
```

### Human

```python
from truthgit.validators import HumanValidator

validators = [
    OllamaValidator("llama3"),
    HumanValidator("reviewer"),  # Interactive CLI prompt
]
```

## Configuration

`.truth/config`:

```json
{
  "version": "1.0.0",
  "consensus_threshold": 0.66,
  "default_verifiers": ["OLLAMA:LLAMA3", "OLLAMA:MISTRAL"]
}
```

## Use Cases

- **Knowledge Bases** — Build verified, auditable knowledge graphs
- **Fact Checking** — Multi-source verification for claims
- **Research** — Track hypotheses and their verification status
- **AI Training Data** — Curate high-quality, verified datasets
- **Documentation** — Version control for technical claims

## Roadmap

**Completed in v0.5.0:**
- [x] Ontological consensus — Classify disagreement types
- [x] Fallacy detection — 11 logical fallacy patterns
- [x] Hypothesis testing — Falsifiability evaluation
- [x] Philosophy domain support — MYSTERY/GAP handling

**Upcoming:**
- [ ] `truthgit mediate` — Human mediation workflow for GAP claims
- [ ] Federation — Sync truth between repositories
- [ ] IPFS Storage — Decentralized content storage
- [ ] Web UI — Visual truth explorer
- [ ] GitHub Integration — Verify claims in issues/PRs
- [ ] VS Code Extension — Inline claim verification

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/truthgit/truthgit
cd truthgit
pip install -e ".[dev]"
pytest
```

## API Reference

### Core Modules

```python
# Ontological consensus
from truthgit.ontological_classifier import (
    calculate_ontological_consensus,
    classify_disagreement,
    DisagreementType,      # LOGICAL_ERROR, MYSTERY, GAP
    ConsensusStatus,       # PASSED, FAILED, UNRESOLVABLE, PENDING_MEDIATION
    OntologicalConsensus,
)

# Fallacy detection
from truthgit.fallacy_detector import (
    detect_fallacies,
    FallacyCategory,  # FORMAL, INFORMAL
    FallacyResult,
    Fallacy,
)

# Hypothesis testing
from truthgit.hypothesis_tester import (
    evaluate_hypothesis,
    EpistemicStatus,  # ESTABLISHED, CONTESTED, SPECULATIVE, FRINGE, UNFALSIFIABLE
    HypothesisType,   # EMPIRICAL, EXISTENTIAL, UNIVERSAL, CAUSAL, MATHEMATICAL
    HypothesisResult,
)

# Repository operations
from truthgit import TruthRepository, Claim, Axiom, Verification
```

### OntologicalConsensus Object

```python
@dataclass
class OntologicalConsensus:
    status: ConsensusStatus           # PASSED, FAILED, UNRESOLVABLE, PENDING_MEDIATION
    value: float                      # Mean confidence (0.0-1.0)
    threshold: float                  # Consensus threshold (default 0.66)
    disagreement_type: DisagreementType | None  # LOGICAL_ERROR, MYSTERY, GAP
    preserved_positions: dict | None  # For MYSTERY: all validator reasonings
    mediation_context: str | None     # For GAP: brief for human mediator
    excluded_validators: list | None  # For LOGICAL_ERROR: which were excluded
    validator_details: dict           # Original validator results
```

## Philosophy

> "In a world where AI can generate infinite content, the scarce resource is verified truth."

TruthGit is built on four principles:

1. **Ontology over counting** — Ask "what type?" before "how much?"
2. **Consensus over authority** — No single source is trusted
3. **Immutability over mutation** — Truth is append-only
4. **Openness over control** — Protocol is open, self-hosting is encouraged

### The Ontological Insight

Traditional verification systems treat all disagreement the same: if validators don't agree, the claim fails. But not all disagreement is equal:

- When a validator makes a **logical error**, exclude it and recalculate
- When the claim is genuinely **unknowable**, preserve the disagreement as data
- When the claim is **unfalsifiable**, escalate to human judgment

This is the philosophical core that makes TruthGit different from simple voting systems.

## License

MIT © [TruthGit](https://truthgit.com)

---

<div align="center">

**[truthgit.com](https://truthgit.com)** — Version control for verified truth.

</div>
