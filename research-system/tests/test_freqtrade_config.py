import json

import pytest
from rsys import freqtrade_config, safety
from rsys.config import load_settings

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


def test_base_config_is_dry_run_without_keys():
    cfg = freqtrade_config.base_config(load_settings(), PAIRS)
    assert cfg["dry_run"] is True
    assert cfg["exchange"]["key"] == "" and cfg["exchange"]["secret"] == ""
    assert cfg["exchange"]["pair_whitelist"] == PAIRS
    assert cfg["trading_mode"] == "spot"


def test_supertrend_config_applies_risk_limits():
    settings = load_settings()
    cfg = freqtrade_config.supertrend_config(settings)
    assert cfg["stoploss"] == pytest.approx(-0.10)
    assert cfg["stake_amount"] == pytest.approx(2000)
    assert cfg["exchange"]["pair_whitelist"] == ["BTC/USDT"]
    assert cfg["rsys_supertrend"]["params_confirmed"] is False


def test_buyhold_splits_equally_across_pairs():
    cfg = freqtrade_config.buyhold_config(PAIRS)
    assert cfg["max_open_trades"] == 3 and cfg["stake_amount"] == "unlimited"


def test_write_all_writes_three_files(tmp_path):
    written = freqtrade_config.write_all(load_settings(), PAIRS, tmp_path)
    assert sorted(p.name for p in written) == [
        "config.base.json",
        "config.buyhold.json",
        "config.supertrend.json",
    ]
    assert json.loads((tmp_path / "config.base.json").read_text())["dry_run"] is True


def test_live_settings_from_example_file_still_dry_run():
    settings = load_settings()
    settings.update(
        trading_mode="live", live_trading_enabled=True, live_trading_ack=safety.LIVE_ACK_PHRASE
    )
    # _source is still the example file, so the lock stays closed.
    assert freqtrade_config.base_config(settings, PAIRS)["dry_run"] is True
