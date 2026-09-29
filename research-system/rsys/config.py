"""Settings loader: config/settings.yaml if present, else config/settings.example.yaml."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
USER_FILE = "settings.yaml"
EXAMPLE_FILE = "settings.example.yaml"


def load_settings(config_dir: Path | None = None) -> dict:
    config_dir = Path(config_dir or os.environ.get("RSYS_CONFIG_DIR") or CONFIG_DIR)
    user_file = config_dir / USER_FILE
    path = user_file if user_file.exists() else config_dir / EXAMPLE_FILE
    settings = yaml.safe_load(path.read_text()) or {}
    settings["_source"] = path.name
    return settings
