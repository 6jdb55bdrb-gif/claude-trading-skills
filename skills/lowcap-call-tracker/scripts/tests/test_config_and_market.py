"""Configuration loading, validation and session-state tests."""

from datetime import datetime

import pytest
import yaml
from market_hours import is_trading_day, session_state

from config import ConfigError, load_config, repo_root, resolve_path


def test_default_config_defines_three_variants(config):
    variants = config["screener"]["variants"]
    assert set(variants) == {"squeeze", "momentum_breakout", "etf_momentum"}


def test_calls_close_at_contract_expiry_by_default(config):
    """Trades are options: the contract's expiry is the only close rule."""
    assert config["tracker"]["close_on_expiry"] is True
    assert config["tracker"]["close_threshold_pct"] is None
    assert config["tracker"]["options"]["default_dte"] == 30


def test_close_rules_are_config_values_not_constants(config):
    """Both the expiry rule and the optional stop-out are read from config."""
    import inspect

    import price_update

    source = inspect.getsource(price_update.update_open_calls)
    assert 'config["tracker"].get("close_threshold_pct")' in source
    assert 'config["tracker"].get("close_on_expiry"' in source
    assert "-80" not in source


def test_a_configured_threshold_is_still_accepted(tmp_path):
    """The early stop-out is disabled, not deleted: a number re-enables it."""
    overlay = tmp_path / "over.yaml"
    overlay.write_text(
        yaml.safe_dump({"tracker": {"close_threshold_pct": -80.0}}), encoding="utf-8"
    )
    assert load_config(overlay)["tracker"]["close_threshold_pct"] == -80.0


def test_removing_every_close_rule_is_rejected(tmp_path):
    overlay = tmp_path / "over.yaml"
    overlay.write_text(
        yaml.safe_dump({"tracker": {"close_on_expiry": False, "close_threshold_pct": None}}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="no close rule"):
        load_config(overlay)


def test_overlay_is_deep_merged(tmp_path):
    overlay = tmp_path / "over.yaml"
    overlay.write_text(
        yaml.safe_dump({"tracker": {"close_threshold_pct": -50.0}}), encoding="utf-8"
    )
    merged = load_config(overlay)
    assert merged["tracker"]["close_threshold_pct"] == -50.0
    # Untouched keys survive the merge.
    assert merged["tracker"]["account_size"] == 1000.0
    assert set(merged["screener"]["variants"]) == {"squeeze", "momentum_breakout", "etf_momentum"}


@pytest.mark.parametrize(
    "overlay",
    [
        {"tracker": {"close_threshold_pct": 80.0}},
        {"screener": {"variants": None}},  # a non-mapping replaces, an empty dict merges
        {"screener": {"variants": {"bad": {"asset_type": "crypto", "filters": ["x"]}}}},
        {"screener": {"variants": {"bad": {"asset_type": "stock", "filters": []}}}},
    ],
)
def test_invalid_config_is_rejected(tmp_path, overlay):
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(overlay), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_resolve_path_is_repo_relative(config):
    assert resolve_path(config, "db_path") == repo_root() / "state" / "lowcap_calls.db"


def test_weekend_blocks_screening(config):
    state = session_state(config, datetime(2026, 9, 19, 11, 0))  # Saturday
    assert state["trading_day"] is False
    assert state["screening_allowed"] is False
    assert "weekend" in state["reason"]


def test_holiday_blocks_screening(config):
    state = session_state(config, datetime(2026, 12, 25, 11, 0))
    assert state["screening_allowed"] is False
    assert "holiday" in state["reason"]


def test_regular_hours_allow_screening(config):
    state = session_state(config, datetime(2026, 9, 18, 10, 0))  # Friday
    assert state["regular_hours"] is True
    assert state["screening_allowed"] is True


def test_extended_hours_allowed_by_default_but_configurable(config):
    evening = datetime(2026, 9, 18, 18, 30)
    assert session_state(config, evening)["screening_allowed"] is True
    config["market"]["allow_extended_hours"] = False
    state = session_state(config, evening)
    assert state["screening_allowed"] is False
    assert state["trading_day"] is True


def test_is_trading_day_handles_iso_holiday_strings(config):
    assert is_trading_day(config, datetime(2026, 9, 18).date()) is True
    assert is_trading_day(config, datetime(2026, 7, 3).date()) is False
