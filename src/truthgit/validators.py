"""
TruthGit Validators - Pluggable verification system.

Supports:
- Local: Ollama (llama3, mistral, phi3, etc.)
- Cloud: Claude, GPT, Gemini (optional, requires API keys)
- Human: Manual verification

Usage:
    # Local-first (no API keys needed)
    validators = [OllamaValidator("llama3"), OllamaValidator("mistral")]

    # With cloud (optional)
    validators = [ClaudeValidator(), GPTValidator(), GeminiValidator()]

    # Mixed
    validators = [OllamaValidator("llama3"), ClaudeValidator()]
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result from a single validator."""

    validator_name: str
    confidence: float
    reasoning: str
    model: str = ""
    tokens_used: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class Validator(ABC):
    """Base class for all validators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this validator."""
        pass

    @abstractmethod
    def validate(self, claim: str, domain: str = "general") -> ValidationResult:
        """
        Validate a claim and return confidence + reasoning.

        Args:
            claim: The statement to validate
            domain: Knowledge domain (e.g., "physics", "history")

        Returns:
            ValidationResult with confidence [0, 1] and reasoning
        """
        pass

    def is_available(self) -> bool:
        """Check if this validator is available (e.g., API key set)."""
        return True


# =============================================================================
# LOCAL VALIDATORS (No API keys required)
# =============================================================================


class OllamaValidator(Validator):
    """
    Validator using Ollama for local LLM inference.

    Requires: ollama installed and running
    Models: llama3, mistral, phi3, gemma, etc.
    """

    PROMPT_TEMPLATE = """\
You are a truth validator. Analyze the following claim and determine its accuracy.

Claim: {claim}
Domain: {domain}

Respond in JSON format:
{{
    "confidence": <float between 0 and 1>,
    "reasoning": "<brief explanation>"
}}

Be objective. If uncertain, reflect that in a lower confidence score."""

    def __init__(self, model: str = "llama3"):
        self.model = model
        self._name = f"OLLAMA:{model.upper()}"

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx

            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def validate(self, claim: str, domain: str = "general") -> ValidationResult:
        try:
            import httpx

            prompt = self.PROMPT_TEMPLATE.format(claim=claim, domain=domain)

            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            text = result.get("response", "{}")

            # Parse JSON response
            try:
                parsed = json.loads(text)
                confidence = float(parsed.get("confidence", 0.5))
                reasoning = parsed.get("reasoning", "No reasoning provided")
            except json.JSONDecodeError:
                # Fallback: try to extract from text
                confidence = 0.5
                reasoning = text[:200] if text else "Could not parse response"

            return ValidationResult(
                validator_name=self.name,
                confidence=min(1.0, max(0.0, confidence)),
                reasoning=reasoning,
                model=self.model,
            )

        except ImportError:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="httpx not installed. Run: pip install httpx",
            )
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error=str(e),
            )


# =============================================================================
# CLOUD VALIDATORS (Require API keys)
# =============================================================================


class ClaudeValidator(Validator):
    """Validator using Anthropic's Claude API."""

    PROMPT = """Analyze this claim for accuracy. Respond with JSON only:
{"confidence": <0-1>, "reasoning": "<brief explanation>"}

Claim: {claim}
Domain: {domain}"""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    @property
    def name(self) -> str:
        return "CLAUDE"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def validate(self, claim: str, domain: str = "general") -> ValidationResult:
        if not self.api_key:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="ANTHROPIC_API_KEY not set",
            )

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[
                    {
                        "role": "user",
                        "content": self.PROMPT.format(claim=claim, domain=domain),
                    }
                ],
            )

            text = response.content[0].text
            parsed = json.loads(text)

            return ValidationResult(
                validator_name=self.name,
                confidence=float(parsed["confidence"]),
                reasoning=parsed["reasoning"],
                model=self.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            )

        except ImportError:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="anthropic not installed. Run: pip install anthropic",
            )
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error=str(e),
            )


class GPTValidator(Validator):
    """Validator using OpenAI's GPT API."""

    PROMPT = """Analyze this claim for accuracy. Respond with JSON only:
{"confidence": <0-1>, "reasoning": "<brief explanation>"}

Claim: {claim}
Domain: {domain}"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

    @property
    def name(self) -> str:
        return "GPT"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def validate(self, claim: str, domain: str = "general") -> ValidationResult:
        if not self.api_key:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="OPENAI_API_KEY not set",
            )

        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": self.PROMPT.format(claim=claim, domain=domain),
                    }
                ],
                max_tokens=256,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content
            parsed = json.loads(text)

            return ValidationResult(
                validator_name=self.name,
                confidence=float(parsed["confidence"]),
                reasoning=parsed["reasoning"],
                model=self.model,
                tokens_used=response.usage.total_tokens,
            )

        except ImportError:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="openai not installed. Run: pip install openai",
            )
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error=str(e),
            )


class GeminiValidator(Validator):
    """Validator using Google's Gemini API."""

    PROMPT = """Analyze this claim for accuracy. Respond with JSON only:
{"confidence": <0-1>, "reasoning": "<brief explanation>"}

Claim: {claim}
Domain: {domain}"""

    def __init__(self, model: str = "gemini-1.5-flash"):
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    @property
    def name(self) -> str:
        return "GEMINI"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def validate(self, claim: str, domain: str = "general") -> ValidationResult:
        if not self.api_key:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="GEMINI_API_KEY not set",
            )

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

            response = model.generate_content(
                self.PROMPT.format(claim=claim, domain=domain),
                generation_config={"response_mime_type": "application/json"},
            )

            parsed = json.loads(response.text)

            return ValidationResult(
                validator_name=self.name,
                confidence=float(parsed["confidence"]),
                reasoning=parsed["reasoning"],
                model=self.model,
            )

        except ImportError:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error="google-generativeai not installed. Run: pip install google-generativeai",
            )
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error=str(e),
            )


# =============================================================================
# HUMAN VALIDATOR
# =============================================================================


class HumanValidator(Validator):
    """Interactive human validation via CLI."""

    def __init__(self, name: str = "HUMAN"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def validate(self, claim: str, domain: str = "general") -> ValidationResult:
        """Prompt human for validation via stdin."""
        print(f"\n{'=' * 60}")
        print("HUMAN VALIDATION REQUIRED")
        print(f"{'=' * 60}")
        print(f"Claim: {claim}")
        print(f"Domain: {domain}")
        print(f"{'=' * 60}")

        try:
            confidence_str = input("Confidence (0-100): ").strip()
            confidence = float(confidence_str) / 100.0
            reasoning = input("Reasoning: ").strip()

            return ValidationResult(
                validator_name=self.name,
                confidence=min(1.0, max(0.0, confidence)),
                reasoning=reasoning,
            )
        except (ValueError, EOFError) as e:
            return ValidationResult(
                validator_name=self.name,
                confidence=0,
                reasoning="",
                error=str(e),
            )


# =============================================================================
# VALIDATOR REGISTRY
# =============================================================================


def get_default_validators(local_only: bool = False) -> list[Validator]:
    """
    Get default validators based on availability.

    Args:
        local_only: If True, only use local validators (Ollama)

    Returns:
        List of available validators
    """
    validators = []

    # Try Ollama first (local, free)
    ollama_models = ["llama3", "mistral", "phi3"]
    for model in ollama_models:
        v = OllamaValidator(model)
        if v.is_available():
            validators.append(v)
            break  # One Ollama model is enough for local

    if local_only:
        # For local mode, use multiple Ollama models for diversity
        for model in ollama_models:
            v = OllamaValidator(model)
            if v.is_available() and v not in validators:
                validators.append(v)
                if len(validators) >= 3:
                    break
    else:
        # Add cloud validators if available
        cloud_validators = [ClaudeValidator(), GPTValidator(), GeminiValidator()]
        for v in cloud_validators:
            if v.is_available():
                validators.append(v)

    return validators


def validate_claim(
    claim: str,
    domain: str = "general",
    validators: list[Validator] | None = None,
    min_validators: int = 2,
) -> tuple[list[ValidationResult], float]:
    """
    Validate a claim using multiple validators.

    Args:
        claim: The statement to validate
        domain: Knowledge domain
        validators: List of validators (default: auto-detect)
        min_validators: Minimum validators required

    Returns:
        Tuple of (results list, average confidence)
    """
    if validators is None:
        validators = get_default_validators()

    if len(validators) < min_validators:
        raise ValueError(
            f"Need at least {min_validators} validators, "
            f"found {len(validators)}. Install Ollama or set API keys."
        )

    results = []
    for v in validators:
        result = v.validate(claim, domain)
        results.append(result)

    # Calculate average confidence (excluding errors)
    successful = [r for r in results if r.success]
    if successful:
        avg_confidence = sum(r.confidence for r in successful) / len(successful)
    else:
        avg_confidence = 0.0

    return results, avg_confidence
