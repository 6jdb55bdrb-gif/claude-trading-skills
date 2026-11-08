#!/usr/bin/env python3
"""Run the full IVB study (variants, robustness grid, GARCH split, chart).

Usage:
  python3 examples/ivb-orb-backtest/run_study.py --source yahoo --output-dir reports/
  APCA_API_KEY_ID=... APCA_API_SECRET_KEY=... \
    python3 examples/ivb-orb-backtest/run_study.py --source alpaca --bar-minutes 5 --ib-minutes 30
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivb_backtest as ivb  # noqa: E402


def equity(trades):
    s = pd.Series([t.ret_pct / 100 for t in trades], index=pd.to_datetime([t.date for t in trades]))
    return (1 + s).cumprod()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="QQQ,SPY")
    ap.add_argument("--source", choices=["yahoo", "alpaca"], default="yahoo")
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--bar-minutes", type=int, default=0)
    ap.add_argument("--ib-minutes", type=int, default=60)
    ap.add_argument("--rvol", type=float, default=1.2, help="IVB volume threshold")
    ap.add_argument("--clv", type=float, default=0.7, help="IVB close-location threshold")
    ap.add_argument("--split", default="2025-01-01", help="in-sample / out-of-sample boundary")
    ap.add_argument("--output-dir", default="reports/")
    a = ap.parse_args()
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    results = {"generated": today, "source": a.source, "symbols": {}}

    base = ivb.Params(ib_minutes=a.ib_minutes, last_entry="15:00", cost_bps=1.0, risk_pct=1.0)
    variants = {
        "A_plain_ORB": base,
        "B_IVB_volume_IBstop": replace(base, rvol_min=a.rvol, clv_min=a.clv),
        "C_IVB_volume_aggrBarStop": replace(
            base, rvol_min=a.rvol, clv_min=a.clv, stop_mode="breakout_bar"
        ),
        "D_IVB_aggrBarStop_2R": replace(
            base, rvol_min=a.rvol, clv_min=a.clv, stop_mode="breakout_bar", target_r=2
        ),
        "E_IVB_aggrBarStop_longOnly": replace(
            base, rvol_min=a.rvol, clv_min=a.clv, stop_mode="breakout_bar", allow_short=False
        ),
    }

    curves = {}
    for sym in a.symbols.split(","):
        if a.source == "yahoo":
            df = ivb.load_yahoo(sym)
        else:
            df = ivb.load_alpaca(sym, a.start, today, "1Min", Path(".cache"))
        if a.bar_minutes:
            df = ivb.resample(df, a.bar_minutes)
        daily = ivb.load_yahoo_daily(sym)
        garch = ivb.garch_forecast(daily["close"])
        first, last = df.index[0].date(), df.index[-1].date()
        bh = daily.loc[str(first) : str(last), "close"]
        bh_ret = bh.pct_change().dropna()
        bh_dd = (bh / bh.cummax() - 1).min()
        sym_res = {
            "period": f"{first} -> {last}",
            "sessions": int(len(set(df.index.date))),
            "buy_hold": {
                "total_return_pct": round((bh.iloc[-1] / bh.iloc[0] - 1) * 100, 2),
                "max_dd_pct": round(bh_dd * 100, 2),
                "sharpe": round(bh_ret.mean() / bh_ret.std() * 252**0.5, 2),
            },
            "variants": {},
        }
        for name, p in variants.items():
            tr = ivb.run_backtest(df, p)
            is_tr = [t for t in tr if t.date < a.split]
            oos_tr = [t for t in tr if t.date >= a.split]
            sym_res["variants"][name] = {
                "label": p.label(),
                "overall": ivb.metrics(tr, 1),
                "in_sample": ivb.metrics(is_tr, 1),
                "out_of_sample": ivb.metrics(oos_tr, 1),
                "by_year": ivb.by_period(tr),
                "by_quarter": ivb.by_period(tr, "Q"),
            }
            curves[f"{sym} {name}"] = equity(tr)
            if name == "C_IVB_volume_aggrBarStop":
                pd.DataFrame([asdict(t) for t in tr]).to_csv(
                    out / f"ivb_trades_{sym}_{today}.csv", index=False
                )
        # GARCH regime split on the main IVB variant
        main_p = variants["C_IVB_volume_aggrBarStop"]
        sym_res["garch_split"] = {
            g: ivb.metrics(ivb.run_backtest(df, replace(main_p, garch_filter=g), garch), 1)
            for g in ("high", "low")
        }
        sym_res["garch_split_plainORB"] = {
            g: ivb.metrics(ivb.run_backtest(df, replace(base, garch_filter=g), garch), 1)
            for g in ("high", "low")
        }
        # robustness grid
        grid = []
        for rv, clv, sm in itertools.product(
            [0, 1.0, 1.2, 1.5], [0, 0.6, 0.7, 0.8], ["ib_opposite", "ib_mid", "breakout_bar"]
        ):
            m = ivb.metrics(
                ivb.run_backtest(df, replace(base, rvol_min=rv, clv_min=clv, stop_mode=sm)), 1
            )
            grid.append(
                {
                    "rvol": rv,
                    "clv": clv,
                    "stop": sm,
                    **{
                        k: m.get(k)
                        for k in (
                            "trades",
                            "win_rate",
                            "avg_r",
                            "profit_factor",
                            "sharpe",
                            "max_dd_pct",
                        )
                    },
                }
            )
        sym_res["grid"] = grid
        g = pd.DataFrame(grid)
        sym_res["grid_summary"] = {
            "combos": len(g),
            "pf_gt_1": int((g.profit_factor > 1).sum()),
            "median_pf": round(float(g.profit_factor.median()), 3),
            "median_sharpe": round(float(g.sharpe.median()), 2),
        }
        results["symbols"][sym] = sym_res
        print(f"[{sym}] done", file=sys.stderr)

    (out / f"ivb_study_{today}.json").write_text(json.dumps(results, indent=2, default=str))
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
        for k, c in curves.items():
            if any(v in k for v in ("A_plain", "C_IVB", "E_IVB")):
                ax.plot(c.index, (c - 1) * 100, label=k, lw=1.4)
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_title("IVB / ORB backtest - equity (% , 1% risk per trade)")
        ax.set_ylabel("Cumulative return %")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out / f"ivb_equity_{today}.png")
    except ImportError:
        pass
    print(
        json.dumps(
            {
                s: {k: v["overall"] for k, v in r["variants"].items()}
                for s, r in results["symbols"].items()
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
