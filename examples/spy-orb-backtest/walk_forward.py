#!/usr/bin/env python3
"""Walk-forward test of ORB settings: pick on past years, score on the next one.

For each test year, every config in the grid is ranked by its total P&L over
all earlier years (expanding window). The winner is then scored on the test
year, which it never saw. Summing those test-year results gives an honest
estimate of what "tune, then trade" would have earned.

    python3 walk_forward.py --csv data/spy_5m.csv --test-years 2024 2025 2026
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from multiprocessing import Pool
from pathlib import Path

from orb_backtest import FOMC_DATES, ORBConfig, backtest, load_csv

_DF = None


def walk_forward(yearly: dict[str, dict[str, float]], test_years: list[str]) -> list[dict]:
    """yearly = {config_name: {year: pnl}} -> one result row per test year."""
    rows = []
    for ty in test_years:
        train = {n: sum(v for y, v in ys.items() if y < ty) for n, ys in yearly.items()}
        best = max(train, key=lambda n: (train[n], n))
        rows.append(
            {
                "test_year": ty,
                "chosen": best,
                "train_pnl": train[best],
                "test_pnl": yearly[best].get(ty, 0),
            }
        )
    return rows


def default_grid(slippage_pct: float) -> dict[str, dict]:
    stops = {
        "pct5": dict(stop_mode="pct"),
        "atr2": dict(stop_mode="atr", atr_mult=2),
        "atr3": dict(stop_mode="atr", atr_mult=3),
        "atr4": dict(stop_mode="atr", atr_mult=4),
    }
    grid = {}
    for (sn, s), hold, fomc, width, tp in itertools.product(
        stops.items(), [None, 60, 120], [False, True], [None, 0.3, 0.4, 0.5], [None, 1.0]
    ):
        name = f"{sn}|hold={hold or 'eod'}|fomc={'skip' if fomc else 'trade'}|w={width or '-'}|tp={tp or '-'}"
        grid[name] = dict(
            s,
            max_hold_minutes=hold,
            skip_dates=FOMC_DATES if fomc else frozenset(),
            max_or_width_rel=width,
            take_profit_pct=tp,
            slippage_pct=slippage_pct,
        )
    return grid


def _init(csv):
    global _DF
    _DF = load_csv(csv)


def _yearly(item):
    name, kw = item
    t = backtest(_DF, ORBConfig(**kw))
    return name, ({} if t.empty else t.groupby(t["date"].str[:4])["pnl"].sum().to_dict())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--csv", required=True)
    p.add_argument("--test-years", nargs="+", default=["2024", "2025", "2026"])
    p.add_argument("--slippage-pct", type=float, default=0.002)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--output", help="Write JSON results here")
    a = p.parse_args(argv)

    grid = default_grid(a.slippage_pct)
    with Pool(a.procs, initializer=_init, initargs=(a.csv,)) as pool:
        yearly = dict(pool.map(_yearly, grid.items()))
    rows = walk_forward(yearly, a.test_years)
    oos = sum(r["test_pnl"] for r in rows)
    for r in rows:
        print(
            f"{r['test_year']}: chose {r['chosen']:55s} train ${r['train_pnl']:8.2f}  test ${r['test_pnl']:8.2f}"
        )
    print(
        f"Walk-forward out-of-sample total: ${oos:.2f} over {len(rows)} years ({len(grid)} configs searched)"
    )
    if a.output:
        Path(a.output).write_text(
            json.dumps({"rows": rows, "oos_total": oos, "yearly": yearly}, indent=2)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
