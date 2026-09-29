import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _example_settings_only(tmp_path_factory, monkeypatch):
    """Tests always see settings.example.yaml, never a user's local settings.yaml."""
    config_dir = tmp_path_factory.mktemp("config")
    shutil.copy(ROOT / "config" / "settings.example.yaml", config_dir)
    monkeypatch.setenv("RSYS_CONFIG_DIR", str(config_dir))
