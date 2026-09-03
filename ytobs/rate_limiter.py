"""Retry handling and helpers for LLM backend adapters.

This module is provider-agnostic: it knows how to retry calls and parse outputs,
but the actual backend calls are delegated to BackendAdapter implementations
(from backend_adapter.py).
"""

import re
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .backend_adapter import BackendAdapter
from .config import ModelConfig


@dataclass
class ModelHandle:
    """Binds a backend adapter to a specific model identifier."""

    adapter: BackendAdapter
    model_id: str
    context_window: int = 200000
    is_thinking_model: bool = False

    @classmethod
    def from_config(
        cls, config: ModelConfig, fabric_command: str = "fabric"
    ) -> "ModelHandle":
        """Build a ModelHandle from a ModelConfig entry."""
        from .backend_adapter import get_adapter

        return cls(
            adapter=get_adapter(config.provider, fabric_command=fabric_command),
            model_id=config.model_id,
            context_window=config.context_window,
        )


# --- ARCHIVED: Groq free tier models (kept for reference) --------------------
# These were used when Fabric routed through Groq API with tight TPM limits.
# @dataclass
# class GroqModel:
#     name: str
#     tpm: int
#
# GROQ_MODELS = {
#     "llama-4-scout": GroqModel("meta-llama/llama-4-scout-17b-16e-instruct", tpm=30000),
#     "kimi":          GroqModel("moonshotai/kimi-k2-instruct-0905",         tpm=10000),
#     "llama-70b":     GroqModel("llama-3.3-70b-versatile",                  tpm=12000),
#     "llama-8b":      GroqModel("llama-3.1-8b-instant",                     tpm=6000),
#     "qwen3":         GroqModel("qwen/qwen3-32b",                           tpm=6000),
# }
# --- End archived ------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    words = len(text.split())
    system_overhead = 800
    return int(words * 1.3) + system_overhead


def validate_request_size(text: str, max_tokens: int = 200000) -> Tuple[bool, str]:
    """Validate request won't exceed model limits."""
    estimated = estimate_tokens(text)
    if estimated > max_tokens:
        return False, f"Request too large: ~{estimated} tokens (max: {max_tokens})"
    return True, ""


def parse_thinking_tags(text: str) -> str:
    """Remove thinking tags from model output."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


@dataclass
class FabricResult:
    """Result from a backend pattern call."""

    success: bool
    output: str = ""
    error: str = ""
    retries: int = 0
    model_used: Optional[str] = None


class RateLimitHandler:
    """Retries pattern calls across one or more ModelHandles."""

    def __init__(
        self,
        models: List[ModelHandle],
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize with an ordered list of models to try.

        Args:
            models: Ordered list of ModelHandles. Primary first, fallbacks after.
            retry_config: Retry configuration.
        """
        self.models = models
        self.retry_config = retry_config or RetryConfig()

    def run_pattern(
        self,
        pattern: str,
        input_text: str,
        timeout: int = 120,
    ) -> FabricResult:
        """Run a pattern, retrying and falling back across models.

        Args:
            pattern: Pattern name.
            input_text: Input text.
            timeout: Timeout in seconds.

        Returns:
            FabricResult with output or error.
        """
        last_error = ""
        total_retries = 0

        for i, model in enumerate(self.models):
            result = self._try_with_retries(model, pattern, input_text, timeout)
            total_retries += result.retries

            if result.success:
                result.retries = total_retries
                return result

            last_error = result.error

            # Only fall back on rate-limit / server errors
            if "429" not in result.error and "rate limit" not in result.error.lower():
                if not any(code in result.error for code in ["500", "502", "503"]):
                    break

            if i < len(self.models) - 1:
                print(f"      🔄 Fallback to: {self.models[i + 1].model_id}")

        return FabricResult(success=False, error=last_error, retries=total_retries)

    def _try_with_retries(
        self,
        model: ModelHandle,
        pattern: str,
        input_text: str,
        timeout: int,
    ) -> FabricResult:
        """Try running a pattern against one model with exponential backoff."""
        retries = 0
        delay = self.retry_config.base_delay
        last_result: Optional[FabricResult] = None

        while retries <= self.retry_config.max_retries:
            adapter_result = model.adapter.run_pattern(
                pattern=pattern,
                input_text=input_text,
                model_id=model.model_id,
                timeout=timeout,
            )

            output = parse_thinking_tags(adapter_result.output)
            result = FabricResult(
                success=adapter_result.success,
                output=output,
                error=adapter_result.error,
                model_used=model.model_id,
            )
            last_result = result

            if result.success:
                return result

            is_rate_limited = (
                "429" in result.error or "rate limit" in result.error.lower()
            )
            is_server_error = any(
                code in result.error for code in ["500", "502", "503"]
            )

            if not (is_rate_limited or is_server_error):
                return result

            retries += 1
            if retries > self.retry_config.max_retries:
                break

            print(
                f"      ⏳ Retry {retries}/{self.retry_config.max_retries} "
                f"after {delay:.1f}s..."
            )
            time.sleep(delay)
            delay = min(
                delay * self.retry_config.exponential_base,
                self.retry_config.max_delay,
            )

        error_msg = last_result.error if last_result else "Unknown error"
        return FabricResult(
            success=False,
            error=f"Max retries exceeded: {error_msg}",
            retries=retries,
            model_used=model.model_id,
        )
