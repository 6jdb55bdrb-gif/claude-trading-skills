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


def _validate(config: dict[str, Any]) -> None:
    for section in ("tracker", "screener", "roles", "llm", "market", "telegram", "learning"):
        if not isinstance(config.get(section), dict):
            raise ConfigError(f"configuration section '{section}' is missing or not a mapping")
    variants = config["screener"].get("variants")
    if not isinstance(variants, dict) or not variants:
        raise ConfigError("screener.variants must be a non-empty mapping")
    for name, variant in variants.items():
        if variant.get("asset_type") not in {"stock", "etf"}:
            raise ConfigError(f"variant '{name}': asset_type must be 'stock' or 'etf'")
        if not variant.get("filters"):
            raise ConfigError(f"variant '{name}': at least one filter code is required")
    threshold = config["tracker"].get("close_threshold_pct")
    if threshold is not None and (not isinstance(threshold, (int, float)) or threshold >= 0):
        raise ConfigError(
            "tracker.close_threshold_pct must be a negative number, or null to disable "
            "the early stop-out (calls then close only at contract expiry)"
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
