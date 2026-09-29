"""Paper-only guard. Live trading needs three fields the user sets by hand in settings.yaml."""

from __future__ import annotations

from .config import USER_FILE

LIVE_ACK_PHRASE = "I ACCEPT REAL MONEY RISK"


class LiveTradingBlocked(RuntimeError):
    pass


def live_trading_allowed(settings: dict) -> bool:
    return (
        settings.get("_source", USER_FILE) == USER_FILE
        and settings.get("trading_mode") == "live"
        and settings.get("live_trading_enabled") is True
        and settings.get("live_trading_ack") == LIVE_ACK_PHRASE
    )


def dry_run_flag(settings: dict) -> bool:
    return not live_trading_allowed(settings)


def assert_freqtrade_config_is_paper(config: dict, settings: dict) -> None:
    """Refuse any engine config that would trade live unless the manual lock is open."""
    exchange = config.get("exchange", {})
    if any(exchange.get(field) for field in ("key", "secret", "password")):
        raise LiveTradingBlocked("exchange credentials must never be written by this system")
    if config.get("dry_run") is not True and not live_trading_allowed(settings):
        raise LiveTradingBlocked(
            "dry_run is not true and live trading was not manually enabled in settings.yaml"
        )
