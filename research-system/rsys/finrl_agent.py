"""DEVELOPER: FinRL PPO agent trading BTC/ETH (spot, long-only) on the canonical daily candles.

Design choices that keep the RL result honest:
- Same canonical CSVs as every other engine; same fee+slippage per side (settings.costs).
- Fixed chronological splits: train < validation < locked holdout (never used for tuning).
- Several seeds; the report shows the spread, not the best seed.
- Indicators are computed per ticker on past data only.
- FinRL's StockTradingEnv trades whole "shares", so prices are rescaled to ~100 units at the
  start of training (e.g. 1 unit = 1/190 BTC). Returns are unchanged by this rescaling.

Run inside the finrl Docker image:  python -m rsys.finrl_agent --timesteps 50000 --seeds 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_DIR, load_settings
from .ohlcv import load_csv

TECH = ["macd", "rsi_14", "cci_20", "sma_ratio_50"]
SPLITS = {  # inclusive start, exclusive end
    "train": ("2022-12-01", "2025-04-01"),
    "validation": ("2025-04-01", "2026-04-01"),
    "holdout": ("2026-04-01", "2100-01-01"),  # locked: report only, never tune on it
}
RESULTS_DIR = DATA_DIR / "results" / "finrl"


def _rsi(close: pd.Series, n: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def _cci(df: pd.DataFrame, n: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(n).mean()
    mad = tp.rolling(n).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma) / (0.015 * mad)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["macd"] = (ema12 - ema26) / out["close"]  # scale-free
    out["rsi_14"] = _rsi(out["close"], 14)
    out["cci_20"] = _cci(out, 20)
    out["sma_ratio_50"] = out["close"] / out["close"].rolling(50).mean() - 1
    return out


def build_frame(pairs: list[str], exchange: str, canonical_dir: Path | None = None) -> pd.DataFrame:
    """Long-format frame in FinRL's layout: date, tic, open, high, low, close, volume, TECH..."""
    canonical_dir = Path(canonical_dir or DATA_DIR / "ohlcv") / exchange
    frames = []
    for pair in pairs:
        df = load_csv(canonical_dir / f"{pair.replace('/', '_')}-1d.csv")
        df = add_indicators(df)
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
        df["tic"] = pair
        frames.append(df)
    data = pd.concat(frames).dropna(subset=TECH)
    # keep only dates where every ticker has a row
    counts = data.groupby("date")["tic"].transform("count")
    data = data[counts == len(pairs)]
    return data.sort_values(["date", "tic"]).reset_index(drop=True)


def rescale_prices(
    data: pd.DataFrame, train_start: str, target: float = 100.0
) -> tuple[pd.DataFrame, dict]:
    """Rescale each ticker's OHLC so its first training close is ~target units."""
    out, scales = data.copy(), {}
    for tic, grp in data.groupby("tic"):
        first = grp.loc[grp["date"] >= train_start, "close"].iloc[0]
        scales[tic] = float(first / target)
        mask = out["tic"] == tic
        out.loc[mask, ["open", "high", "low", "close"]] /= scales[tic]
    return out, scales


def split(data: pd.DataFrame, name: str) -> pd.DataFrame:
    start, end = SPLITS[name]
    part = data[(data["date"] >= start) & (data["date"] < end)].copy()
    part.index = part["date"].factorize()[0]
    return part


def buy_and_hold_curve(part: pd.DataFrame, initial: float) -> pd.Series:
    """Equal-weight buy & hold (no rebalancing) over the same split, for comparison."""
    closes = part.pivot(index="date", columns="tic", values="close")
    growth = closes / closes.iloc[0]
    return initial * growth.mean(axis=1)


def summarize(curve: pd.Series) -> dict:
    curve = pd.Series(np.asarray(curve, dtype=float))
    rets = curve.pct_change().dropna()
    drawdown = (curve / curve.cummax() - 1).min()
    downside = rets[rets < 0].std()
    ann = np.sqrt(365)
    return {
        "total_return_pct": round(float(curve.iloc[-1] / curve.iloc[0] - 1) * 100, 2),
        "max_drawdown_pct": round(float(drawdown) * 100, 2),
        "sharpe": round(float(rets.mean() / rets.std() * ann), 2) if rets.std() > 0 else None,
        "sortino": round(float(rets.mean() / downside * ann), 2)
        if downside and downside > 0
        else None,
        "days": int(len(curve)),
    }


def _make_env(part: pd.DataFrame, cost: float, initial: float):
    from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv

    stock_dim = part["tic"].nunique()
    return StockTradingEnv(
        df=part,
        stock_dim=stock_dim,
        hmax=100,
        initial_amount=initial,
        num_stock_shares=[0] * stock_dim,
        buy_cost_pct=[cost] * stock_dim,
        sell_cost_pct=[cost] * stock_dim,
        reward_scaling=1e-4,
        state_space=1 + 2 * stock_dim + len(TECH) * stock_dim,
        action_space=stock_dim,
        tech_indicator_list=TECH,
        make_plots=False,
        print_verbosity=10**9,
    )


def run(
    pairs: list[str],
    timesteps: int,
    seeds: list[int],
    settings: dict,
    evaluate_holdout: bool = False,
) -> dict:
    from finrl.agents.stablebaselines3.models import DRLAgent

    costs = settings["costs"]
    cost = (costs["fee_pct_per_side"] + costs["slippage_pct_per_side"]) / 100
    initial = float(settings["paper"]["starting_wallet_usdt"])
    data = build_frame(pairs, settings["data"]["exchange"])
    data, scales = rescale_prices(data, SPLITS["train"][0])
    eval_splits = ["validation", "holdout"] if evaluate_holdout else ["validation"]
    parts = {name: split(data, name) for name in ["train", *eval_splits]}
    report = {
        "role": "DEVELOPER",
        "engine": "FinRL StockTradingEnv + SB3 PPO",
        "pairs": pairs,
        "cost_per_side": cost,
        "timesteps": timesteps,
        "price_unit_scales": scales,
        "splits": {k: [str(v["date"].min()), str(v["date"].max())] for k, v in parts.items()},
        "baseline_buy_and_hold": {
            k: summarize(buy_and_hold_curve(v, initial)) for k, v in parts.items()
        },
        "seeds": {},
    }
    for seed in seeds:
        env_train, _ = _make_env(parts["train"], cost, initial).get_sb_env()
        agent = DRLAgent(env=env_train)
        model = agent.get_model("ppo", seed=seed, verbose=0)
        model = agent.train_model(model=model, tb_log_name=f"ppo_{seed}", total_timesteps=timesteps)
        seed_report = {}
        for name in eval_splits:
            account, _actions = DRLAgent.DRL_prediction(
                model=model, environment=_make_env(parts[name], cost, initial)
            )
            seed_report[name] = summarize(account["account_value"])
        report["seeds"][str(seed)] = seed_report
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FinRL PPO agent (paper research only)")
    parser.add_argument("--pairs", nargs="*", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument(
        "--evaluate-holdout",
        action="store_true",
        help="BACKTESTER final run only: also score the locked holdout window",
    )
    args = parser.parse_args(argv)
    report = run(
        args.pairs,
        args.timesteps,
        list(range(args.seeds)),
        load_settings(),
        evaluate_holdout=args.evaluate_holdout,
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_with_holdout" if args.evaluate_holdout else ""
    out = RESULTS_DIR / f"finrl_ppo_{args.timesteps}steps_{args.seeds}seeds{suffix}.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"[DEVELOPER] FinRL report -> {out}")
    print(
        json.dumps(
            {"baseline": report["baseline_buy_and_hold"], "seeds": report["seeds"]}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
