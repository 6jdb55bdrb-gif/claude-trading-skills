#!/usr/bin/env python3
"""Backtest the ICT Silver Bullet across symbols and timeframes.

Example::

    python3 skills/ict-silver-bullet/scripts/backtest_silver_bullet.py \
        --symbols BTC=binance:BTCUSDT,SPY=yahoo:SPY,QQQ=yahoo:QQQ,NQ=yahoo:NQ=F \
        --timeframes 1m,5m,15m --days 365 --grid --output-dir reports/

For every (symbol, timeframe) the runner reports:

* the canonical configuration's statistics (in R, net of costs),
* a per-window breakdown (London / AM / PM),
* a chronological first-half vs. second-half split (stability check),
* optionally (``--grid``) a parameter-sensitivity grid: the share of nearby
  configurations that are still profitable. A real edge should not live on a
  single parameter knife-edge.

Exit codes: 0 success, 1 error, 2 missing optional dependency.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pandas as pd  # noqa: E402
from data_sources import load_bars, parse_source  # noqa: E402
from silver_bullet import SilverBulletParams, prepare_bars, run_backtest, summarize  # noqa: E402

DEFAULT_SYMBOLS = "BTC=binance:BTCUSDT,SPY=yahoo:SPY,QQQ=yahoo:QQQ,ES=yahoo:ES=F,NQ=yahoo:NQ=F"
DEFAULT_COST_BPS = {"binance": 2.0, "yahoo": 0.5, "csv": 1.0}
MIN_TRADES_FOR_VERDICT = 30

GRID = {
    "entry_mode": ["edge", "ce"],
    "target": [("liquidity", 1.5), ("liquidity", 2.0), ("rr", 2.0), ("rr", 3.0)],
    "require_mss": [True, False],
    "displacement_atr": [0.3, 0.5, 0.8],
    "bias_filter": ["none", "sma"],
}


def parse_symbols(text: str) -> list[tuple[str, str]]:
    out = []
    for item in filter(None, (s.strip() for s in text.split(","))):
        if "=" not in item:
            raise ValueError(f"symbol spec must be NAME=source:id (got {item!r})")
        name, spec = item.split("=", 1)
        parse_source(spec)
        out.append((name.strip(), spec.strip()))
    if not out:
        raise ValueError("no symbols given")
    return out


def grid_params(base: SilverBulletParams) -> list[SilverBulletParams]:
    out = []
    for entry, (tmode, tval), mss, disp, bias in itertools.product(*GRID.values()):
        kw = {
            "entry_mode": entry,
            "target_mode": tmode,
            "require_mss": mss,
            "displacement_atr": disp,
            "bias_filter": bias,
        }
        kw["min_rr" if tmode == "liquidity" else "rr_target"] = tval
        out.append(replace(base, **kw))
    return out


def split_halves(trades, start, end):
    mid = start + (end - start) / 2
    first = [t for t in trades if pd.Timestamp(t.entry_time) < mid]
    second = [t for t in trades if pd.Timestamp(t.entry_time) >= mid]
    return first, second


def verdict(stats: dict, halves: tuple[dict, dict], grid_share: float | None) -> str:
    n = stats.get("trades", 0)
    if n < MIN_TRADES_FOR_VERDICT:
        return "INSUFFICIENT_SAMPLE"
    exp = stats["expectancy_r"]
    ci_lo = stats["expectancy_ci95"][0]
    both = all(h.get("trades", 0) > 0 and h["expectancy_r"] > 0 for h in halves)
    grid_ok = grid_share is None or grid_share >= 0.6
    if exp > 0 and ci_lo > 0 and both and grid_ok:
        return "ROBUST_EDGE"
    if exp > 0 and both:
        return "POSITIVE_UNCONFIRMED"
    if exp > 0:
        return "UNSTABLE"
    return "NO_EDGE"


def evaluate(name, spec, tf, bars, base, run_grid):
    first_ts, last_ts = bars.index.min(), bars.index.max()
    trades, diags = run_backtest(bars, base)
    stats = summarize(trades)
    halves = split_halves(trades, first_ts, last_ts)
    half_stats = (summarize(halves[0]), summarize(halves[1]))
    by_window = {w: summarize([t for t in trades if t.window == w]) for w in base.windows}
    status_counts: dict[str, int] = {}
    for d in diags:
        status_counts[d["status"]] = status_counts.get(d["status"], 0) + 1
    grid_rows, grid_share = [], None
    if run_grid:
        for gp in grid_params(base):
            gt, _ = run_backtest(bars, gp)
            gs = summarize(gt)
            grid_rows.append(
                {
                    "entry_mode": gp.entry_mode,
                    "target": f"{gp.target_mode}:{gp.min_rr if gp.target_mode == 'liquidity' else gp.rr_target}",
                    "require_mss": gp.require_mss,
                    "displacement_atr": gp.displacement_atr,
                    "bias_filter": gp.bias_filter,
                    "trades": gs.get("trades", 0),
                    "expectancy_r": gs.get("expectancy_r"),
                    "win_rate": gs.get("win_rate"),
                    "profit_factor": gs.get("profit_factor"),
                }
            )
        valid = [g for g in grid_rows if g["trades"] >= 10]
        if valid:
            grid_share = round(sum(1 for g in valid if g["expectancy_r"] > 0) / len(valid), 3)
    return {
        "symbol": name,
        "source": spec,
        "timeframe": tf,
        "period": [first_ts.isoformat(), last_ts.isoformat()],
        "bars": int(len(bars)),
        "stats": stats,
        "first_half": half_stats[0],
        "second_half": half_stats[1],
        "by_window": by_window,
        "window_status": status_counts,
        "grid_positive_share": grid_share,
        "grid": grid_rows,
        "verdict": verdict(stats, half_stats, grid_share),
        "trades": [t.__dict__ for t in trades],
    }


def _fmt(x, digits=2):
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def render_markdown(results: list[dict], params: SilverBulletParams, generated: str) -> str:
    lines = [
        "# ICT Silver Bullet Backtest",
        "",
        f"**Generated:** {generated}  ",
        f"**Windows (America/New_York):** {', '.join(params.windows)}  ",
        f"**Canonical rules:** sweep={params.require_sweep}, MSS={params.require_mss}, "
        f"entry={params.entry_mode}, target={params.target_mode} "
        f"(min {params.min_rr}R / rr {params.rr_target}R), displacement>={params.displacement_atr} ATR, "
        f"FVG>={params.min_fvg_atr} ATR, ref range={params.ref_lookback_minutes} min "
        f"(sweep may start {params.sweep_lead_minutes} min pre-window), bias={params.bias_filter}, "
        f"max cost {params.max_cost_r}R, "
        f"flat {params.flat_minutes_after_window} min after window",
        "",
        "All results are in R (multiples of initial risk), net of per-side costs. "
        "Same-bar stop/target ambiguity is resolved as a loss.",
        "",
        "## Summary",
        "",
        "| Symbol | TF | Days | Trades | Win% | Exp R | 95% CI | PF | Total R | MaxDD R | H1 Exp | H2 Exp | Grid+ | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        s = r["stats"]
        days = (pd.Timestamp(r["period"][1]) - pd.Timestamp(r["period"][0])).days
        if s.get("trades", 0) == 0:
            lines.append(
                f"| {r['symbol']} | {r['timeframe']} | {days} | 0 | – | – | – | – | – | – | – | – | – | {r['verdict']} |"
            )
            continue
        ci = s["expectancy_ci95"]
        gshare = r["grid_positive_share"]
        grid_txt = "–" if gshare is None else f"{gshare * 100:.0f}%"
        lines.append(
            f"| {r['symbol']} | {r['timeframe']} | {days} | {s['trades']} | {s['win_rate'] * 100:.0f}% | "
            f"{_fmt(s['expectancy_r'], 3)} | [{ci[0]:.2f}, {ci[1]:.2f}] | {_fmt(s['profit_factor'])} | "
            f"{_fmt(s['total_r'], 1)} | {_fmt(s['max_drawdown_r'], 1)} | "
            f"{_fmt(r['first_half'].get('expectancy_r'), 3)} | {_fmt(r['second_half'].get('expectancy_r'), 3)} | "
            f"{grid_txt} | "
            f"**{r['verdict']}** |"
        )
    lines += [
        "",
        "## Per-window breakdown",
        "",
        "| Symbol | TF | Window | Trades | Win% | Exp R | Total R |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        for w, s in r["by_window"].items():
            if s.get("trades", 0) == 0:
                lines.append(f"| {r['symbol']} | {r['timeframe']} | {w} | 0 | – | – | – |")
            else:
                lines.append(
                    f"| {r['symbol']} | {r['timeframe']} | {w} | {s['trades']} | {s['win_rate'] * 100:.0f}% | "
                    f"{s['expectancy_r']:.3f} | {s['total_r']:.1f} |"
                )
    if any(r["grid"] for r in results):
        lines += ["", "## Best / worst grid configurations (>=10 trades)", ""]
        for r in results:
            valid = [g for g in r["grid"] if g["trades"] >= 10]
            if not valid:
                continue
            valid.sort(key=lambda g: g["expectancy_r"], reverse=True)
            best, worst = valid[0], valid[-1]
            lines.append(
                f"- **{r['symbol']} {r['timeframe']}** — best: {best['entry_mode']}/{best['target']}/"
                f"MSS={best['require_mss']}/disp={best['displacement_atr']}/bias={best['bias_filter']} → {best['expectancy_r']:.3f}R "
                f"({best['trades']} tr); worst: {worst['entry_mode']}/{worst['target']}/MSS={worst['require_mss']}/"
                f"disp={worst['displacement_atr']}/bias={worst['bias_filter']} → {worst['expectancy_r']:.3f}R ({worst['trades']} tr)"
            )
    lines += [
        "",
        "## Verdict legend",
        "",
        "- **ROBUST_EDGE** — expectancy > 0, bootstrap 95% CI excludes 0, both halves positive, ≥60% of grid neighbours positive.",
        "- **Grid+** — share of the 96 sensitivity-grid configurations (with ≥10 trades) that are profitable after costs.",
        "- **POSITIVE_UNCONFIRMED** — positive in both halves but not statistically significant (or grid fragile).",
        "- **UNSTABLE** — positive overall but one half negative.",
        "- **NO_EDGE** — expectancy ≤ 0 after costs.",
        f"- **INSUFFICIENT_SAMPLE** — fewer than {MIN_TRADES_FOR_VERDICT} trades.",
        "",
        "_Backtests are hypothetical, exclude slippage beyond the modelled cost, and do not guarantee future results._",
    ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--symbols", default=DEFAULT_SYMBOLS, help="comma list of NAME=source:id")
    ap.add_argument("--timeframes", default="1m,5m,15m")
    ap.add_argument(
        "--days", type=int, default=365, help="history to request (Yahoo caps intraday history)"
    )
    ap.add_argument("--windows", default="london,am,pm")
    ap.add_argument("--entry-mode", choices=["edge", "ce"], default="edge")
    ap.add_argument("--target-mode", choices=["liquidity", "rr"], default="liquidity")
    ap.add_argument("--min-rr", type=float, default=1.5)
    ap.add_argument("--rr-target", type=float, default=2.0)
    ap.add_argument("--no-sweep", action="store_true", help="do not require a liquidity sweep")
    ap.add_argument("--no-mss", action="store_true", help="do not require a market-structure shift")
    ap.add_argument("--displacement-atr", type=float, default=0.5)
    ap.add_argument("--min-fvg-atr", type=float, default=0.10)
    ap.add_argument("--ref-lookback-minutes", type=int, default=120)
    ap.add_argument("--sweep-lead-minutes", type=int, default=30)
    ap.add_argument(
        "--bias", choices=["none", "sma"], default="none", help="daily trend bias filter"
    )
    ap.add_argument(
        "--max-cost-r",
        type=float,
        default=0.10,
        help="skip setups whose round-trip cost exceeds this R",
    )
    ap.add_argument("--flat-minutes", type=int, default=60)
    ap.add_argument(
        "--cost-bps", default="", help="per-side cost override: NAME=bps,... (defaults by source)"
    )
    ap.add_argument("--include-weekends", action="store_true", help="crypto: also trade Sat/Sun")
    ap.add_argument("--grid", action="store_true", help="run the parameter-sensitivity grid")
    ap.add_argument("--cache-dir", default=".cache/ict-silver-bullet")
    ap.add_argument("--output-dir", default="reports/")
    ap.add_argument("--no-trades", action="store_true", help="omit per-trade rows from the JSON")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        symbols = parse_symbols(args.symbols)
        tfs = [t.strip() for t in args.timeframes.split(",") if t.strip()]
        overrides = {}
        for item in filter(None, args.cost_bps.split(",")):
            k, v = item.split("=", 1)
            overrides[k.strip()] = float(v)
        base = SilverBulletParams(
            windows=tuple(w.strip() for w in args.windows.split(",") if w.strip()),
            ref_lookback_minutes=args.ref_lookback_minutes,
            sweep_lead_minutes=args.sweep_lead_minutes,
            bias_filter=args.bias,
            max_cost_r=args.max_cost_r,
            require_sweep=not args.no_sweep,
            require_mss=not args.no_mss,
            displacement_atr=args.displacement_atr,
            min_fvg_atr=args.min_fvg_atr,
            entry_mode=args.entry_mode,
            target_mode=args.target_mode,
            min_rr=args.min_rr,
            rr_target=args.rr_target,
            flat_minutes_after_window=args.flat_minutes,
            include_weekends=args.include_weekends,
        )
        base.validate()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    results = []
    for name, spec in symbols:
        kind = spec.split(":", 1)[0].lower()
        p = replace(base, cost_bps=overrides.get(name, DEFAULT_COST_BPS[kind]))
        for tf in tfs:
            print(f"[{name} {tf}] loading {spec} ...", file=sys.stderr)
            try:
                raw = load_bars(spec, tf, args.days, Path(args.cache_dir))
                bars = prepare_bars(raw)
            except (ValueError, RuntimeError) as exc:
                print(f"[{name} {tf}] skipped: {exc}", file=sys.stderr)
                continue
            res = evaluate(name, spec, tf, bars, p, args.grid)
            res["cost_bps"] = p.cost_bps
            if args.no_trades:
                res.pop("trades")
            s = res["stats"]
            print(
                f"[{name} {tf}] {len(bars)} bars, {s.get('trades', 0)} trades, "
                f"exp={s.get('expectancy_r')}R -> {res['verdict']}",
                file=sys.stderr,
            )
            results.append(res)

    if not results:
        print("error: no results (all data loads failed)", file=sys.stderr)
        return 1
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = out_dir / f"ict_silver_bullet_backtest_{stamp}.md"
    json_path = out_dir / f"ict_silver_bullet_backtest_{stamp}.json"
    md_path.write_text(render_markdown(results, base, generated), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {"generated": generated, "params": base.to_dict(), "results": results},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"wrote {md_path} and {json_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
