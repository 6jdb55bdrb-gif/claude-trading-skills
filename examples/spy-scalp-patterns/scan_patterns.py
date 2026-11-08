#!/usr/bin/env python3
"""Scan SPY intraday bars for Stochastic / MACD / 50-MA patterns.

For every pattern, measure what SPY did next: enter at the NEXT bar's open,
exit at the close h bars later (same session only), in basis points
(1 bp = 0.01%). Results are split in-sample (before --split) and
out-of-sample (from --split on); a real pattern should work in both.

    python3 scan_patterns.py --csv ../spy-orb-backtest/data/spy_5m.csv --horizons 1 3 6 12
    python3 scan_patterns.py --csv ../spy-orb-backtest/data/spy_1m.csv --horizons 1 5 10 15 30
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spy-orb-backtest"))
from indicators import add_indicators  # noqa: E402

# (name, expected direction) -- +1 = bullish pattern, -1 = bearish pattern
PATTERNS: list[tuple[str, int]] = [
    ("stoch_cross_up_oversold", 1),
    ("stoch_cross_down_overbought", -1),
    ("stoch_cross_up_any", 1),
    ("stoch_cross_down_any", -1),
    ("stoch_leaves_oversold", 1),
    ("stoch_leaves_overbought", -1),
    ("macd_cross_up", 1),
    ("macd_cross_down", -1),
    ("macd_cross_up_below_zero", 1),
    ("macd_cross_down_above_zero", -1),
    ("macd_zero_cross_up", 1),
    ("macd_zero_cross_down", -1),
    ("hist_turns_up", 1),
    ("hist_turns_down", -1),
    ("price_crosses_above_ma50", 1),
    ("price_crosses_below_ma50", -1),
    ("uptrend_pullback_stoch_up", 1),
    ("downtrend_rally_stoch_down", -1),
    ("downtrend_stoch_up_fade", 1),
    ("uptrend_stoch_down_fade", -1),
    ("uptrend_macd_cross_up", 1),
    ("downtrend_macd_cross_down", -1),
    ("uptrend_stoch_up_hist_rising", 1),
    ("downtrend_stoch_down_hist_falling", -1),
    ("macd_up_with_stoch_low", 1),
    ("macd_down_with_stoch_high", -1),
    ("oversold_below_ma_reversion", 1),
    ("overbought_above_ma_reversion", -1),
]


def crosses_above(a: pd.Series, b) -> pd.Series:
    b_prev = b.shift(1) if isinstance(b, pd.Series) else b
    return ((a > b) & (a.shift(1) <= b_prev)).fillna(False)


def crosses_below(a: pd.Series, b) -> pd.Series:
    b_prev = b.shift(1) if isinstance(b, pd.Series) else b
    return ((a < b) & (a.shift(1) >= b_prev)).fillna(False)


def events(
    df: pd.DataFrame, ma: int = 50, os_level: float = 20, ob_level: float = 80
) -> pd.DataFrame:
    """Boolean column per pattern, using only data up to and including each bar."""
    x = add_indicators(df, ma=ma)
    k, d, m, sig, h, c, sm = (
        x["stoch_k"],
        x["stoch_d"],
        x["macd"],
        x["macd_signal"],
        x["macd_hist"],
        x["close"],
        x[f"sma{ma}"],
    )
    up_trend = (c > sm) & (sm > sm.shift(10))
    dn_trend = (c < sm) & (sm < sm.shift(10))
    k_up, k_dn = crosses_above(k, d), crosses_below(k, d)
    m_up, m_dn = crosses_above(m, sig), crosses_below(m, sig)
    hist_up, hist_dn = h > h.shift(1), h < h.shift(1)
    e = {
        "stoch_cross_up_oversold": k_up & (d < os_level),
        "stoch_cross_down_overbought": k_dn & (d > ob_level),
        "stoch_cross_up_any": k_up,
        "stoch_cross_down_any": k_dn,
        "stoch_leaves_oversold": crosses_above(k, os_level),
        "stoch_leaves_overbought": crosses_below(k, ob_level),
        "macd_cross_up": m_up,
        "macd_cross_down": m_dn,
        "macd_cross_up_below_zero": m_up & (m < 0),
        "macd_cross_down_above_zero": m_dn & (m > 0),
        "macd_zero_cross_up": crosses_above(m, 0),
        "macd_zero_cross_down": crosses_below(m, 0),
        "hist_turns_up": hist_up & (h.shift(1) <= h.shift(2)),
        "hist_turns_down": hist_dn & (h.shift(1) >= h.shift(2)),
        "price_crosses_above_ma50": crosses_above(c, sm),
        "price_crosses_below_ma50": crosses_below(c, sm),
        "uptrend_pullback_stoch_up": up_trend & k_up & (d < os_level),
        "downtrend_rally_stoch_down": dn_trend & k_dn & (d > ob_level),
        "downtrend_stoch_up_fade": dn_trend & k_up & (d < os_level),
        "uptrend_stoch_down_fade": up_trend & k_dn & (d > ob_level),
        "uptrend_macd_cross_up": up_trend & m_up,
        "downtrend_macd_cross_down": dn_trend & m_dn,
        "uptrend_stoch_up_hist_rising": up_trend & k_up & (d < 50) & hist_up,
        "downtrend_stoch_down_hist_falling": dn_trend & k_dn & (d > 50) & hist_dn,
        "macd_up_with_stoch_low": m_up & (k < 30),
        "macd_down_with_stoch_high": m_dn & (k > 70),
        "oversold_below_ma_reversion": k_up & (d < os_level) & (c < sm),
        "overbought_above_ma_reversion": k_dn & (d > ob_level) & (c > sm),
    }
    out = pd.DataFrame(e, index=df.index).fillna(False).astype(bool)
    return out[[n for n, _ in PATTERNS]]


def states(df: pd.DataFrame, ma: int = 50) -> pd.DataFrame:
    """Coarse indicator state per bar, for the exhaustive grid scan."""
    x = add_indicators(df, ma=ma)
    k, d = x["stoch_k"], x["stoch_d"]
    sm = x[f"sma{ma}"]
    return pd.DataFrame(
        {
            "stoch": np.select([k < 20, k > 80], ["OS", "OB"], "mid"),
            "stoch_x": np.select(
                [crosses_above(k, d), crosses_below(k, d)], ["up", "down"], "none"
            ),
            "macd_vs_sig": np.where(x["macd"] > x["macd_signal"], "above", "below"),
            "macd_vs_0": np.where(x["macd"] > 0, "pos", "neg"),
            "vs_ma50": np.where(x["close"] > sm, "above", "below"),
            "ma50_slope": np.where(sm > sm.shift(10), "up", "down"),
        },
        index=df.index,
    ).where(sm.notna() & k.notna())


def forward_returns(df: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """bps from next bar's open to the close h bars later; NaN if it leaves the session."""
    day = pd.Series(df.index.date, index=df.index)
    nxt_open = df["open"].shift(-1)
    out = {}
    for h in horizons:
        exit_close = df["close"].shift(-h)
        same = day.shift(-h) == day
        out[f"fwd_{h}"] = ((exit_close / nxt_open - 1) * 1e4).where(same)
    return pd.DataFrame(out, index=df.index)


def summarize(mask: pd.Series, fwd: pd.Series, split: str = "2025-01-01") -> dict:
    sel = fwd[mask.reindex(fwd.index, fill_value=False)].dropna()
    cut = pd.Timestamp(split, tz=sel.index.tz) if len(sel) else None
    res = {}
    for tag, part in (
        ("is", sel[sel.index < cut] if cut is not None else sel),
        ("oos", sel[sel.index >= cut] if cut is not None else sel),
    ):
        n = len(part)
        mean = float(part.mean()) if n else np.nan
        sd = float(part.std(ddof=1)) if n > 1 else np.nan
        res[f"n_{tag}"] = n
        res[f"mean_{tag}"] = mean
        res[f"t_{tag}"] = mean / sd * np.sqrt(n) if n > 1 and sd > 0 else np.nan
        res[f"hit_{tag}"] = float((part > 0).mean() * 100) if n else np.nan
    return res


def scan(df: pd.DataFrame, horizons: list[int], split: str) -> pd.DataFrame:
    ev, fwd = events(df), forward_returns(df, horizons)
    base = {h: summarize(pd.Series(True, index=df.index), fwd[f"fwd_{h}"], split) for h in horizons}
    rows = []
    for (name, sign), h in itertools.product(PATTERNS, horizons):
        r = summarize(ev[name], fwd[f"fwd_{h}"], split)
        b = base[h]
        rows.append(
            {
                "pattern": name,
                "dir": "long" if sign == 1 else "short",
                "h": h,
                "n_is": r["n_is"],
                # edge = return in the pattern's direction, minus the average bar's drift
                "edge_is": sign * (r["mean_is"] - b["mean_is"]),
                "t_is": sign * r["t_is"],
                "n_oos": r["n_oos"],
                "edge_oos": sign * (r["mean_oos"] - b["mean_oos"]),
                "t_oos": sign * r["t_oos"],
                "gross_oos": sign * r["mean_oos"],
            }
        )
    return pd.DataFrame(rows)


def grid_scan(df: pd.DataFrame, h: int, split: str, min_n: int = 300) -> pd.DataFrame:
    st, fwd = states(df), forward_returns(df, [h])[f"fwd_{h}"]
    st = st.dropna()
    keys = list(st.columns)
    base = summarize(pd.Series(True, index=df.index), fwd, split)
    rows = []
    for combo, grp in st.groupby(keys):
        r = summarize(pd.Series(True, index=grp.index), fwd, split)
        if r["n_is"] < min_n or r["n_oos"] < min_n // 2:
            continue
        rows.append(
            {
                **dict(zip(keys, combo)),
                **r,
                "ex_is": r["mean_is"] - base["mean_is"],
                "ex_oos": r["mean_oos"] - base["mean_oos"],
            }
        )
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    from orb_backtest import load_csv

    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--csv", required=True)
    p.add_argument("--horizons", type=int, nargs="+", default=[1, 3, 6, 12])
    p.add_argument("--split", default="2025-01-01")
    p.add_argument(
        "--grid-horizon", type=int, help="Also run the exhaustive state grid at this horizon"
    )
    p.add_argument("--output-dir", default="reports/")
    a = p.parse_args(argv)

    df = load_csv(a.csv)
    res = scan(df, a.horizons, a.split)
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.csv).stem
    res.to_csv(out / f"patterns_{stem}.csv", index=False)
    pd.set_option("display.width", 220)
    print(res.round(2).to_string(index=False))
    if a.grid_horizon:
        g = grid_scan(df, a.grid_horizon, a.split)
        g.to_csv(out / f"grid_{stem}_h{a.grid_horizon}.csv", index=False)
        print(g.sort_values("t_is").round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
