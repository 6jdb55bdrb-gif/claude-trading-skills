import pytest
from rsys import safety
from rsys.config import load_settings


def _settings(**overrides):
    base = {"trading_mode": "paper", "live_trading_enabled": False, "live_trading_ack": ""}
    base.update(overrides)
    return base


def test_default_example_settings_are_paper():
    settings = load_settings()
    assert settings["trading_mode"] == "paper"
    assert safety.live_trading_allowed(settings) is False
    assert safety.dry_run_flag(settings) is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"trading_mode": "live"},
        {"trading_mode": "live", "live_trading_enabled": True},
        {"trading_mode": "live", "live_trading_ack": safety.LIVE_ACK_PHRASE},
        {"live_trading_enabled": True, "live_trading_ack": safety.LIVE_ACK_PHRASE},
        {
            "trading_mode": "live",
            "live_trading_enabled": "true",  # string, not a real boolean
            "live_trading_ack": safety.LIVE_ACK_PHRASE,
        },
        {
            "trading_mode": "live",
            "live_trading_enabled": True,
            "live_trading_ack": safety.LIVE_ACK_PHRASE.lower(),
        },
    ],
)
def test_live_requires_all_three_manual_fields(overrides):
    assert safety.live_trading_allowed(_settings(**overrides)) is False


def test_live_allowed_only_with_all_three():
    settings = _settings(
        trading_mode="live",
        live_trading_enabled=True,
        live_trading_ack=safety.LIVE_ACK_PHRASE,
    )
    assert safety.live_trading_allowed(settings) is True
    assert safety.dry_run_flag(settings) is False


def test_example_file_can_never_enable_live(tmp_path):
    example = tmp_path / "settings.example.yaml"
    example.write_text(
        "trading_mode: live\nlive_trading_enabled: true\n"
        f'live_trading_ack: "{safety.LIVE_ACK_PHRASE}"\n'
    )
    settings = load_settings(config_dir=tmp_path)
    assert safety.live_trading_allowed(settings) is False


def test_assert_config_is_paper_rejects_live_freqtrade_config():
    with pytest.raises(safety.LiveTradingBlocked):
        safety.assert_freqtrade_config_is_paper({"dry_run": False}, _settings())
    safety.assert_freqtrade_config_is_paper({"dry_run": True}, _settings())


def test_freqtrade_config_must_not_contain_exchange_keys():
    cfg = {"dry_run": True, "exchange": {"key": "abc", "secret": ""}}
    with pytest.raises(safety.LiveTradingBlocked):
        safety.assert_freqtrade_config_is_paper(cfg, _settings())
