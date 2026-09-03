"""Provider-agnostic backend adapters for LLM calls.

The codebase used to call Fabric CLI directly with hardcoded Groq model names.
This module introduces a small adapter layer so the orchestrator can talk to
any backend that implements the BackendAdapter protocol.

Today only FabricAdapter is implemented. Future adapters (OpenCode, OpenAI,
Anthropic, local Ollama) can be added here without touching the orchestrator.
"""

import subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Protocol


@dataclass
class AdapterResult:
    """Result from a backend adapter call."""

    success: bool
    output: str = ""
    error: str = ""


class BackendAdapter(Protocol):
    """Protocol for LLM backend adapters.

    Implementations must be callable objects that accept a pattern, input text,
    model identifier, and timeout, then return an AdapterResult.
    """

    def run_pattern(
        self,
        pattern: str,
        input_text: str,
        model_id: str,
        timeout: int,
    ) -> AdapterResult: ...


class FabricAdapter:
    """Adapter for the Fabric CLI backend."""

    def __init__(self, fabric_command: str = "fabric"):
        self.fabric_command = fabric_command

    def run_pattern(
        self,
        pattern: str,
        input_text: str,
        model_id: str,
        timeout: int,
    ) -> AdapterResult:
        """Run a Fabric pattern via subprocess.

        Args:
            pattern: Fabric pattern name.
            input_text: Input text (enriched packet).
            model_id: Fabric model tag (e.g., "minimax-m2.7").
            timeout: Timeout in seconds.

        Returns:
            AdapterResult with output or error.
        """
        cmd = [self.fabric_command, "-p", pattern]
        if model_id:
            cmd.extend(["-m", model_id])

        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if result.returncode != 0:
                error_text = result.stderr or f"Exit code {result.returncode}"
                return AdapterResult(
                    success=False,
                    error=error_text[:300],
                )

            return AdapterResult(
                success=True,
                output=result.stdout.strip(),
            )

        except subprocess.TimeoutExpired:
            return AdapterResult(
                success=False,
                error=f"Timeout after {timeout}s",
            )
        except Exception as e:
            return AdapterResult(
                success=False,
                error=str(e),
            )


# Registry of implemented adapters. Add new providers here.
ADAPTER_REGISTRY: Dict[str, type] = {
    "fabric": FabricAdapter,
}


def get_adapter(provider: str, fabric_command: str = "fabric") -> BackendAdapter:
    """Get a backend adapter instance for the given provider.

    Args:
        provider: Provider name (e.g., "fabric").
        fabric_command: Fabric CLI command, used when provider is "fabric".

    Returns:
        BackendAdapter instance.

    Raises:
        ValueError: If the provider is not implemented.
    """
    provider = provider.lower()
    if provider not in ADAPTER_REGISTRY:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Implemented providers: {list(ADAPTER_REGISTRY.keys())}"
        )

    if provider == "fabric":
        return FabricAdapter(fabric_command=fabric_command)

    return ADAPTER_REGISTRY[provider]()
