"""Health checks for the ytobs pipeline.

`ytobs doctor` is the entry point for any failure session: it verifies env,
config resolution, API keys (never printing them), endpoint reachability,
fabric pattern loading, and smoke-tests the primary model through the real
adapter. Each check that has ever failed in a live session lives here so the
same failure class can never require manual re-derivation again.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

from .backend_adapter import (
    FABRIC_PATTERNS_DIR,
    OPENCODE_AUTH_PATH,
    resolve_api_key,
)
from .config import Config, resolve_model, resolve_model_config

SMOKE_PROMPT = "Reply with just OK."
LUSOFONA_URL = "https://modelos.ai.ulusofona.pt"
OPENCODE_ENDPOINTS = {
    "https://opencode.ai/zen/go/v1",
    "https://opencode.ai/zen/v1",
}
QUOTA_STATE_PATH = Path.home() / ".local" / "share" / "opencode" / "quota-state.json"


class CheckResult:
    def __init__(self, name: str, ok: bool, detail: str = "", warn: bool = False):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.warn = warn

    @property
    def icon(self) -> str:
        if self.ok:
            return "✅"
        return "⚠️" if self.warn else "❌"


def _check_env() -> list:
    results = []
    obsvault = os.environ.get("OBSVAULT")
    if not obsvault:
        results.append(CheckResult("OBSVAULT env var", False, "not set"))
    else:
        results.append(CheckResult("OBSVAULT env var", True, obsvault))
        out_dir = Path(obsvault) / "youtube"
        results.append(
            CheckResult(
                "Output dir exists",
                out_dir.exists(),
                str(out_dir),
                warn=True,
            )
        )
    cache_dir = Path.home() / ".yt-obsidian" / "cache"
    results.append(
        CheckResult(
            "Cache dir writable",
            cache_dir.exists() and os.access(cache_dir, os.W_OK),
            str(cache_dir),
        )
    )
    return results


def _check_config(config: Config) -> tuple:
    results = []
    alias = resolve_model(config.model, config)
    try:
        primary = resolve_model_config(alias, config)
        results.append(
            CheckResult(
                f"model '{config.model}' resolves",
                True,
                f"{primary.provider}/{primary.model_id}",
            )
        )
    except Exception as e:
        results.append(CheckResult(f"model '{config.model}' resolves", False, str(e)))
        return results, None, []

    chain = [
        a
        for a in getattr(config, "fallback_models", [])
        if a != alias and a in config.models
    ]
    missing = [
        a for a in getattr(config, "fallback_models", []) if a not in config.models
    ]
    results.append(
        CheckResult(
            "fallback chain",
            True,
            " → ".join(chain) + (f" (ignored: {missing})" if missing else ""),
            warn=bool(missing),
        )
    )
    return results, primary, chain


def _check_keys(config: Config) -> list:
    results = []
    for alias, mc in config.models.items():
        if mc.provider != "openai-compat" and not getattr(mc, "base_url", None):
            continue
        if getattr(mc, "base_url", None) and mc.base_url not in OPENCODE_ENDPOINTS:
            marker = "custom"
        else:
            marker = "opencode"
        key = resolve_api_key(mc)
        env_name = getattr(mc, "api_key_env", None)
        detail = f"{marker}"
        if env_name and not os.environ.get(env_name):
            detail += f" (env {env_name} unset → auth.json)"
        results.append(
            CheckResult(f"key: {alias} ({mc.model_id})", key is not None, detail)
        )
    return results


def _check_fabric(config: Config) -> list:
    results = []
    cmd = config.fabric_command
    found = shutil.which(cmd)
    results.append(
        CheckResult("fabric binary", found is not None, found or "not found", warn=True)
    )
    system_md = FABRIC_PATTERNS_DIR / "extract_wisdom" / "system.md"
    results.append(
        CheckResult(
            "fabric patterns dir",
            system_md.exists(),
            f"{system_md} ({'loadable' if system_md.exists() else 'MISSING — openai-compat adapter depends on it'})",
        )
    )
    return results


def _check_endpoints(config: Config) -> list:
    results = []
    for url in sorted(OPENCODE_ENDPOINTS):
        try:
            r = requests.get(f"{url}/models", timeout=10)
            n = len(r.json().get("data", [])) if r.status_code == 200 else 0
            results.append(
                CheckResult(
                    f"endpoint {url}",
                    r.status_code == 200,
                    f"HTTP {r.status_code}, {n} models",
                )
            )
        except requests.RequestException as e:
            results.append(CheckResult(f"endpoint {url}", False, str(e)[:80]))
    try:
        r = requests.get(LUSOFONA_URL, timeout=10)
        up = r.status_code == 200
        results.append(
            CheckResult(
                "Lusófona (pt)",
                up,
                f"HTTP {r.status_code}" + ("" if up else " — still down"),
                warn=True,
            )
        )
    except requests.RequestException as e:
        results.append(CheckResult("Lusófona (pt)", False, str(e)[:80], warn=True))
    return results


def _smoke_openai_compat(mc, timeout: int = 90) -> tuple:
    key = resolve_api_key(mc)
    if not key:
        return False, "no API key"
    try:
        t0 = time.time()
        r = requests.post(
            f"{mc.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "ytobs-doctor/1.0",
            },
            json={
                "model": mc.model_id,
                "messages": [{"role": "user", "content": SMOKE_PROMPT}],
                "max_tokens": 5,
            },
            timeout=(10, timeout),
        )
        dt = time.time() - t0
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:120]}"
        data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        usage = data.get("usage", {})
        finish = (data.get("choices") or [{}])[0].get("finish_reason")
        if not content and finish == "length":
            return (
                True,
                f"{dt:.1f}s · budget too small to reach content "
                f"(finish=length) — endpoint live",
            )
        return (
            bool(content),
            f"{dt:.1f}s · {usage.get('prompt_tokens', '?')} in / "
            f"{usage.get('completion_tokens', '?')} out · '{(content or '')[:20]}'",
        )
    except requests.RequestException as e:
        return False, str(e)[:120]


def _smoke_fabric(mc, config: Config, timeout: int = 90) -> tuple:
    cmd = [config.fabric_command, "-m", mc.model_id]
    try:
        r = subprocess.run(
            cmd, input=SMOKE_PROMPT, capture_output=True, text=True, timeout=timeout
        )
        if r.returncode != 0:
            return False, (r.stderr or f"exit {r.returncode}")[:120]
        return True, f"out: {r.stdout.strip()[:40]!r}"
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except Exception as e:
        return False, str(e)[:120]


def _check_quota() -> list:
    results = []
    try:
        data = json.loads(QUOTA_STATE_PATH.read_text())
        age_min = int((time.time() - QUOTA_STATE_PATH.stat().st_mtime) / 60)
        parts = []
        for name, entry in data.items():
            if isinstance(entry, dict):
                five = entry.get("5h") or entry.get("five_hour") or {}
                pct = five.get("used_percent") or five.get("percent")
                if pct is not None:
                    parts.append(f"{name}: {pct}% of 5h")
        detail = ", ".join(parts) if parts else json.dumps(data)[:80]
        results.append(
            CheckResult(
                "quota state",
                True,
                f"age {age_min}m · {detail}" + (" (STALE)" if age_min > 15 else ""),
                warn=age_min > 15,
            )
        )
    except FileNotFoundError:
        results.append(
            CheckResult(
                "quota state",
                True,
                f"{QUOTA_STATE_PATH} missing — run `npm run quota:poll` in ~/.config/opencode",
                warn=True,
            )
        )
    except (OSError, json.JSONDecodeError, ValueError) as e:
        results.append(CheckResult("quota state", False, str(e)[:80], warn=True))
    return results


def run_doctor(config: Config, model_override: str = None, full: bool = False) -> int:
    """Run all health checks. Returns exit code (0 green, 1 has failures)."""
    print("\n🩺 ytobs doctor — pipeline health check\n")

    results = []
    results.extend(_check_env())
    cfg_results, primary, _chain = _check_config(config)
    results.extend(cfg_results)

    if model_override:
        alias = resolve_model(model_override, config)
        primary = resolve_model_config(alias, config)
        print(f"   (smoke target overridden: {alias})")

    results.extend(_check_keys(config))
    results.extend(_check_fabric(config))
    results.extend(_check_endpoints(config))
    results.extend(_check_quota())

    for r in results:
        print(f"  {r.icon} {r.name:32} {r.detail}")

    print(f"\n  Smoke test: {primary.provider}/{primary.model_id}")
    if primary.provider == "openai-compat":
        ok, detail = _smoke_openai_compat(primary)
    elif full:
        ok, detail = _smoke_fabric(primary, config)
    else:
        ok, detail = True, "skipped (fabric provider — rerun with --full)"
    print(f"  {'✅' if ok else '❌'} {'smoke':32} {detail}")

    failures = [r for r in results if not r.ok and not r.warn]
    warnings = [r for r in results if r.warn and not r.ok]
    hard_fail = not ok
    print()
    if hard_fail or failures:
        print(f"  ❌ NOT HEALTHY — {len(failures) + int(hard_fail)} failure(s)")
        print("     Follow the breakage tree: docs/AGENTIC_GRAPH.md §4")
        return 1
    if warnings:
        print(f"  ⚠️  HEALTHY with {len(warnings)} warning(s)")
        return 0
    print("  ✅ ALL GREEN")
    return 0
