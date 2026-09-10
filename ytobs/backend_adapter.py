"""Provider-agnostic backend adapters for LLM calls.

The codebase used to call Fabric CLI directly with hardcoded Groq model names.
This module is the adapter layer so the orchestrator can talk to any backend
that implements the BackendAdapter protocol.

Two transports are implemented:

- FabricAdapter: shells out to the Fabric CLI (pattern library + vendors).
  When the ModelConfig carries a base_url, fabric is pointed at that
  OpenAI-compatible gateway via its LiteLLM vendor (env injection only —
  the stored fabric .env is never touched).

- OpenAICompatAdapter: calls OpenAI-compatible /chat/completions endpoints
  directly (no subprocess). Fabric patterns are consumed as plain prompt
  files from ~/.config/fabric/patterns/<pattern>/system.md, so the whole
  fabric pattern library stays available without the CLI in the loop.

API keys are resolved from (in order): an explicit environment variable
(`api_key_env`), or an OpenCode auth.json provider entry (`auth_provider`,
e.g. "opencode-go" or "opencode"). Key values are never logged.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Protocol

import requests

OPENCODE_AUTH_PATH = Path.home() / ".local" / "share" / "opencode" / "auth.json"
FABRIC_PATTERNS_DIR = Path.home() / ".config" / "fabric" / "patterns"


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


def resolve_api_key(model_config) -> Optional[str]:
    """Resolve an API key for a ModelConfig without ever logging the value.

    Order: explicit env var (api_key_env) → OpenCode auth.json provider
    (auth_provider). Returns None when nothing is found.
    """
    if model_config is None:
        return None
    env_name = getattr(model_config, "api_key_env", None)
    if env_name:
        value = os.environ.get(env_name)
        if value:
            return value
    provider = getattr(model_config, "auth_provider", None)
    if provider:
        try:
            auth = json.loads(OPENCODE_AUTH_PATH.read_text())
            return auth.get(provider, {}).get("key") or None
        except (OSError, json.JSONDecodeError, AttributeError):
            return None
    return None


class FabricAdapter:
    """Adapter for the Fabric CLI backend."""

    def __init__(self, fabric_command: str = "fabric", model_config=None):
        self.fabric_command = fabric_command
        self.model_config = model_config

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

        env = os.environ.copy()
        cfg = self.model_config
        base_url = getattr(cfg, "base_url", None) if cfg else None
        if base_url:
            vendor = getattr(cfg, "vendor", None) or "LiteLLM"
            cmd.extend(["--vendor", vendor])
            env["LITELLM_API_BASE_URL"] = base_url
            key = resolve_api_key(cfg)
            if key:
                env["LITELLM_API_KEY"] = key
        if getattr(cfg, "raw", False):
            cmd.append("-r")

        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
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


def load_pattern_messages(pattern: str, input_text: str):
    """Load a Fabric pattern as chat messages.

    Fabric patterns are a directory with system.md; {{input}} marks where the
    user input is embedded. When present, the filled template is sent as a
    single user message (strict-template-safe, mirrors the patched fabric
    behavior of promoting lone system payloads). When absent, the template
    becomes the system message and the input the user message.
    """
    system_md_path = FABRIC_PATTERNS_DIR / pattern / "system.md"
    system_md = system_md_path.read_text()
    if "{{input}}" in system_md:
        return [{"role": "user", "content": system_md.replace("{{input}}", input_text)}]
    return [
        {"role": "system", "content": system_md},
        {"role": "user", "content": input_text},
    ]


class OpenAICompatAdapter:
    """Direct OpenAI-compatible chat/completions adapter (no subprocess).

    Streams the response to survive long reasoning phases (streaming keeps
    bytes flowing, avoiding gateway idle timeouts) and parses SSE deltas.
    """

    def __init__(self, model_config=None):
        self.model_config = model_config

    def run_pattern(
        self,
        pattern: str,
        input_text: str,
        model_id: str,
        timeout: int,
    ) -> AdapterResult:
        cfg = self.model_config
        base_url = (getattr(cfg, "base_url", None) if cfg else None) or ""
        if not base_url:
            return AdapterResult(
                success=False, error="openai-compat provider requires base_url"
            )
        key = resolve_api_key(cfg)
        if not key:
            return AdapterResult(
                success=False,
                error="No API key resolved (set api_key_env or auth_provider)",
            )

        try:
            messages = load_pattern_messages(pattern, input_text)
        except OSError as e:
            return AdapterResult(
                success=False,
                error=f"Pattern '{pattern}' not loadable from {FABRIC_PATTERNS_DIR}: {e}",
            )

        payload = {
            "model": model_id or (cfg.model_id if cfg else ""),
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        max_out = getattr(cfg, "max_output_tokens", None) if cfg else None
        if max_out:
            payload["max_tokens"] = int(max_out)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "ytobs-pipeline/4.1",
        }

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
                timeout=(10, timeout),
            )
        except requests.RequestException as e:
            return AdapterResult(success=False, error=str(e)[:300])

        if resp.status_code != 200:
            body = ""
            try:
                body = resp.text[:300]
            except Exception:
                pass
            return AdapterResult(
                success=False, error=f"HTTP {resp.status_code}: {body}"
            )

        chunks = []
        finish_reason = None
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if obj.get("error"):
                    return AdapterResult(
                        success=False,
                        error=str(obj["error"].get("message") or obj["error"])[:300],
                    )
                usage = obj.get("usage")
                if usage:
                    prompt_t = usage.get("prompt_tokens")
                    compl_t = usage.get("completion_tokens")
                    if prompt_t or compl_t:
                        print(f"      📊 tokens: {prompt_t} in / {compl_t} out")
                for choice in obj.get("choices") or []:
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content:
                        chunks.append(content)
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
        finally:
            resp.close()

        output = "".join(chunks).strip()
        if not output:
            if finish_reason == "length":
                return AdapterResult(
                    success=False,
                    error=(
                        "Model exhausted max_output_tokens on reasoning without "
                        "producing any content — raise max_output_tokens or use a "
                        "non-reasoning model"
                    ),
                )
            return AdapterResult(success=False, error="Empty response from stream")
        return AdapterResult(success=True, output=output)


# Registry of implemented adapters. Add new providers here.
ADAPTER_REGISTRY: Dict[str, type] = {
    "fabric": FabricAdapter,
    "openai-compat": OpenAICompatAdapter,
}


def get_adapter(
    provider: str, fabric_command: str = "fabric", model_config=None
) -> BackendAdapter:
    """Get a backend adapter instance for the given provider.

    Args:
        provider: Provider name (e.g., "fabric", "openai-compat").
        fabric_command: Fabric CLI command, used when provider is "fabric".
        model_config: Optional ModelConfig carrying base_url / key info.

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
        return FabricAdapter(fabric_command=fabric_command, model_config=model_config)

    return ADAPTER_REGISTRY[provider](model_config=model_config)
