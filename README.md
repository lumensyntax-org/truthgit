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

[OLLAMA:LLAMA3] 94% - Accurate under standard atmospheric pressure
[OLLAMA:MISTRAL] 92% - True at 1 atm, varies with altitude
[OLLAMA:PHI3] 95% - Correct for pure water at sea level

✓ PASSED Consensus: 94%
Verification: a7f3b2c1
```

## Why TruthGit?

In a world of AI-generated content, misinformation, and information overload, we need **infrastructure for verified truth**.

TruthGit provides:
- **Immutable storage** — Claims are stored by their content hash (like Git)
- **Multi-validator consensus** — No single AI is trusted alone
- **Auditable history** — Every verification is traceable
- **Local-first** — Works offline with Ollama, no API keys required
- **Open protocol** — Self-host, federate, integrate

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
| `truthgit verify [--local]` | Verify claims with consensus |
| `truthgit status` | Show repository status |
| `truthgit log` | Show verification history |
| `truthgit cat <hash>` | Show object details |
| `truthgit validators` | Show available validators |

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

### 2. Multi-Validator Consensus

Claims are verified by multiple independent validators:

```
        ┌─────────────┐
        │   Claim     │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌───────┐  ┌───────┐  ┌───────┐
│Llama3 │  │Mistral│  │ Phi3  │
│  92%  │  │  88%  │  │  90%  │
└───────┘  └───────┘  └───────┘
               │
               ▼
        ┌─────────────┐
        │ Consensus   │
        │    90%      │
        │  ✓ PASSED   │
        └─────────────┘
```

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

# Verify with multiple validators
verification = repo.verify(
    verifier_results={
        "LLAMA3": (0.95, "Mass-energy equivalence"),
        "MISTRAL": (0.92, "Einstein's famous equation"),
        "PHI3": (0.94, "Verified relationship"),
    }
)

print(f"Consensus: {verification.consensus.value:.0%}")
# Consensus: 94%
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

## Philosophy

> "In a world where AI can generate infinite content, the scarce resource is verified truth."

TruthGit is built on three principles:

1. **Consensus over authority** — No single source is trusted
2. **Immutability over mutation** — Truth is append-only
3. **Openness over control** — Protocol is open, self-hosting is encouraged

## License

MIT © [TruthGit](https://truthgit.com)

---

<div align="center">

**[truthgit.com](https://truthgit.com)** — Version control for verified truth.

</div>
