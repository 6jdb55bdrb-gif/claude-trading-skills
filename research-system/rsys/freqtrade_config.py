"""DEVELOPER: generate paper-only freqtrade configs from settings.yaml + the universe.

config.base.json       shared exchange / wallet / data settings (dry_run forced by safety)
config.buyhold.json    baseline: equal-weight buy & hold, 1d, no exits
config.supertrend.json SuperTrend on one pair with the risk limits applied
"""

from __future__ import annotations

import json
from pathlib import Path

from . import safety


def base_config(settings: dict, pairs: list[str]) -> dict:
    data = settings["data"]
    config = {
        "bot_name": "rsys-paper",
        "dry_run": safety.dry_run_flag(settings),
        "dry_run_wallet": settings["paper"]["starting_wallet_usdt"],
        "stake_currency": data["quote"],
        "stake_amount": "unlimited",
        "tradable_balance_ratio": 0.99,
        "fiat_display_currency": "USD",
        "trading_mode": "spot",
        "margin_mode": "",
        "max_open_trades": 1,
        "cancel_open_orders_on_exit": False,
        "unfilledtimeout": {"entry": 10, "exit": 10, "exit_timeout_count": 0, "unit": "minutes"},
        # Market orders crossing the spread ("other"): realistic fills, needed by lookahead-analysis.
        "order_types": {
            "entry": "market",
            "exit": "market",
            "stoploss": "market",
            "stoploss_on_exchange": False,
        },
        "entry_pricing": {
            "price_side": "other",
            "use_order_book": True,
            "order_book_top": 1,
            "price_last_balance": 0.0,
            "check_depth_of_market": {"enabled": False, "bids_to_ask_delta": 1},
        },
        "exit_pricing": {"price_side": "other", "use_order_book": True, "order_book_top": 1},
        "exchange": {
            "name": data["exchange"],
            "key": "",
            "secret": "",
            "password": "",
            # Honour HTTPS_PROXY / CA bundle env vars (harmless when none are set).
            "ccxt_config": {"requests_trust_env": True},
            "ccxt_async_config": {"aiohttp_trust_env": True},
            "pair_whitelist": pairs,
            "pair_blacklist": [],
        },
        "pairlists": [{"method": "StaticPairList"}],
        "dataformat_ohlcv": "json",
        "telegram": {"enabled": False, "token": "", "chat_id": ""},
        "initial_state": "running",
        "force_entry_enable": False,
        "internals": {"process_throttle_secs": 5},
    }
    safety.assert_freqtrade_config_is_paper(config, settings)
    return config


def buyhold_config(pairs: list[str]) -> dict:
    return {
        "strategy": "BuyAndHold",
        "timeframe": "1d",
        "max_open_trades": len(pairs),
        "stake_amount": "unlimited",
        "stoploss": -0.99,  # baseline is exempt from the stoploss rule by design
    }


def supertrend_config(settings: dict) -> dict:
    st, risk = settings["supertrend"], settings["risk"]
    wallet = settings["paper"]["starting_wallet_usdt"]
    return {
        "strategy": "SuperTrendStrategy",
        "timeframe": st["timeframe"],
        "max_open_trades": 1,
        "stake_amount": round(wallet * risk["max_position_pct"] / 100, 2),
        "stoploss": -risk["stoploss_pct"] / 100,
        "exchange": {"pair_whitelist": [st["pair"]]},
        "rsys_supertrend": {
            "atr_period": st["atr_period"],
            "multiplier": st["multiplier"],
            "params_confirmed": st["params_confirmed"],
        },
    }


def write_all(settings: dict, pairs: list[str], user_data: Path) -> list[Path]:
    user_data = Path(user_data)
    user_data.mkdir(parents=True, exist_ok=True)
    files = {
        "config.base.json": base_config(settings, pairs),
        "config.buyhold.json": buyhold_config(pairs),
        "config.supertrend.json": supertrend_config(settings),
    }
    written = []
    for name, content in files.items():
        path = user_data / name
        path.write_text(json.dumps(content, indent=2) + "\n")
        written.append(path)
    return written
