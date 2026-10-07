#!/usr/bin/env python3
"""Configuration loading for the lowcap call tracker.

The packaged default lives in ``assets/tracker_config.yaml``. A caller may pass
``--config path.yaml`` with a partial document; it is deep-merged over the
default so a deployment only states what it changes.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

try:  # pragma: no cover - exercised indirectly
    import yaml

    HAS_YAML = True
except ImportError:  # pragma: no cover - guarded by config_error()
    HAS_YAML = False

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_ROOT / "assets" / "tracker_config.yaml"


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or is structurally invalid."""


def load_dotenv(path: str | os.PathLike[str] | None = None, *, override: bool = False) -> list[str]:
    """Load ``KEY=value`` lines from a ``.env`` file into the environment.

    Deliberately tiny and dependency-free. A real environment variable always
    wins unless *override* is set, so a deployment cannot be surprised by a
    stale file. Returns the names loaded (never the values — these are secrets).
    """
    target = Path(path) if path else repo_root() / ".env"
    if not target.is_file():
        return []
    loaded: list[str] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        if not key:
            continue
        value = value.strip().strip("'\"")
        if override or key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def repo_root() -> Path:
    """Return the repository root (the directory holding ``skills/``).

    Falls back to the current working directory when the skill is used
    standalone (e.g. unpacked from a ``.skill`` archive).
    """
    for parent in Path(__file__).resolve().parents:
        if parent.name != "skills" and (parent / "skills").is_dir():
            return parent
    return Path.cwd()


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_yaml(path: Path) -> dict[str, Any]:
    if not HAS_YAML:
        raise ConfigError(
            "pyyaml is required to read the tracker configuration. "
            "Install it with: pip install -r requirements.txt"
        )
    if not path.is_file():
        raise ConfigError(f"configuration file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"configuration root must be a mapping: {path}")
    return data


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load the default configuration, deep-merged with *path* when given."""
    config = load_yaml(DEFAULT_CONFIG_PATH)
    if path:
        config = _deep_merge(config, load_yaml(Path(path)))
    _validate(config)
    return config


def _validate_screener_versions(config: dict[str, Any]) -> None:
    """Check every screener version, not only the active one.

    A config carrying both v1 and v2 must keep both runnable, so a mistake in
    the dormant generation has to fail loudly now rather than the next time the
    switch is flipped. A pre-versions config (plain ``screener.variants``) is
    still accepted and read as v1.
    """
    screener = config["screener"]
    versions = screener.get("versions")
    if versions is None:
        blocks = {"v1": {"variants": screener.get("variants")}}
    else:
        if not isinstance(versions, dict) or not versions:
            raise ConfigError("screener.versions must be a non-empty mapping")
        if "variants" in screener:
            raise ConfigError(
                "screener.variants and screener.versions cannot both be set: the "
                "top-level variants block would be silently ignored. Put the "
                "variants under screener.versions.<version>.variants"
            )
        blocks = versions
        active = str(screener.get("screener_version", "v1")).strip().lower()
        if active not in versions:
            raise ConfigError(
                f"screener.screener_version is {active!r} but screener.versions has "
                f"only: {', '.join(sorted(versions))}"
            )

    for version, block in blocks.items():
        if not isinstance(block, dict):
            raise ConfigError(f"screener version '{version}' must be a mapping")
        variants = block.get("variants")
        if not isinstance(variants, dict) or not variants:
            raise ConfigError(f"screener version '{version}': variants must be a non-empty mapping")
        for name, variant in variants.items():
            where = f"version '{version}' variant '{name}'"
            if not isinstance(variant, dict):
                raise ConfigError(f"{where}: must be a mapping")
            if variant.get("asset_type") not in {"stock", "etf"}:
                raise ConfigError(f"{where}: asset_type must be 'stock' or 'etf'")
            if not variant.get("filters"):
                raise ConfigError(f"{where}: at least one filter code is required")
        guards = block.get("guards") or {}
        cap = guards.get("max_change_pct")
        if cap is not None and (not isinstance(cap, (int, float)) or cap <= 0):
            raise ConfigError(
                f"screener version '{version}': guards.max_change_pct must be a "
                "positive number, or absent to allow any move"
            )
        for rung in guards.get("short_float_bonus") or []:
            if not isinstance(rung, dict) or "min_pct" not in rung or "bonus" not in rung:
                raise ConfigError(
                    f"screener version '{version}': each guards.short_float_bonus entry "
                    "needs min_pct and bonus"
                )
        _validate_explosion_signals(version, block.get("explosion_signals"))


# SEC fair access publishes 10 requests/second as the ceiling.
EDGAR_MAX_RATE = 10


def _validate_explosion_signals(version: str, block: Any) -> None:
    """Check the signals layer of one version, if it has one."""
    if block is None:
        return
    where = f"screener version '{version}': explosion_signals"
    if not isinstance(block, dict):
        raise ConfigError(f"{where} must be a mapping")

    cap = block.get("max_total_bonus")
    if cap is not None and (not isinstance(cap, (int, float)) or cap <= 0):
        raise ConfigError(
            f"{where}.max_total_bonus must be a positive number of confidence points, "
            "or absent to let the layer score without a ceiling"
        )

    rate = (block.get("edgar") or {}).get("max_requests_per_second")
    if rate is not None and (not isinstance(rate, (int, float)) or not 0 < rate <= EDGAR_MAX_RATE):
        raise ConfigError(
            f"{where}.edgar.max_requests_per_second must be between 0 and "
            f"{EDGAR_MAX_RATE}: SEC fair access publishes {EDGAR_MAX_RATE}/second as the ceiling"
        )

    for name, spec in (block.get("signals") or {}).items():
        if not isinstance(spec, dict):
            raise ConfigError(f"{where}.signals.{name} must be a mapping")
        for rung in spec.get("rungs") or []:
            if not isinstance(rung, dict) or "min_x" not in rung or "points" not in rung:
                raise ConfigError(f"{where}.signals.{name}: each rung needs min_x and points")

    for name, spec in (block.get("hard_skips") or {}).items():
        if not isinstance(spec, dict):
            raise ConfigError(f"{where}.hard_skips.{name} must be a mapping")


def _validate(config: dict[str, Any]) -> None:
    for section in ("tracker", "screener", "roles", "llm", "market", "telegram", "learning"):
        if not isinstance(config.get(section), dict):
            raise ConfigError(f"configuration section '{section}' is missing or not a mapping")
    _validate_screener_versions(config)
    threshold = config["tracker"].get("close_threshold_pct")
    if threshold is not None and (not isinstance(threshold, (int, float)) or threshold >= 0):
        raise ConfigError(
            "tracker.close_threshold_pct must be a negative number, or null to disable "
            "the early stop-out (calls then close only at contract expiry)"
        )
    sl_pct = config["tracker"].get("sl_pct")
    if sl_pct is not None and (not isinstance(sl_pct, (int, float)) or not 0 < sl_pct < 100):
        raise ConfigError(
            "tracker.sl_pct must be a percentage strictly between 0 and 100 "
            "(it is subtracted from the entry price), or null to disable the fixed stop"
        )
    mode = str(config["telegram"].get("access_mode", "invite")).lower()
    if mode not in ("invite", "open", "closed"):
        raise ConfigError(
            f"telegram.access_mode must be 'invite', 'open' or 'closed' (got {mode!r})"
        )
    if not config["tracker"].get("close_on_expiry", True) and threshold is None:
        raise ConfigError(
            "no close rule configured: set tracker.close_on_expiry true, or give "
            "tracker.close_threshold_pct a negative number"
        )


def resolve_path(
    config: dict[str, Any],
    key: str,
    *,
    base: Path | None = None,
    section: str = "tracker",
) -> Path:
    """Resolve a ``<section>.<key>`` path against the repository root."""
    raw = (config.get(section) or {}).get(key)
    if not raw:
        raise ConfigError(f"{section}.{key} is not configured")
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (base or repo_root()) / candidate
