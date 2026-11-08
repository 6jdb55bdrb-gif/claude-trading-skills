# SPY Scalping Pattern Scan: Stochastic, MACD, 50 MA

Searches SPY 1-minute and 5-minute bars for patterns built from three indicators:
Stochastic (14,3,3), MACD (12,26,9) and a 50-bar simple moving average.

Each pattern is measured honestly: signal on a closed bar, entry at the **next** bar's open,
exit at the close *h* bars later inside the same session. Results are split in-sample
(2022-11 → 2024) and out-of-sample (2025 → 2026-11); a usable pattern must work in both.

```bash
# 28 named patterns x several holding periods
python3 examples/spy-scalp-patterns/scan_patterns.py --csv examples/spy-orb-backtest/data/spy_5m.csv --horizons 1 3 6 12 --grid-horizon 6
python3 examples/spy-scalp-patterns/scan_patterns.py --csv examples/spy-orb-backtest/data/spy_1m.csv --horizons 1 5 10 15 30 --grid-horizon 10
```

Data comes from `examples/spy-orb-backtest/fetch_alpaca_bars.py` (`--timeframe 1Min` for 1-minute bars).

## Findings (Nov 2022 – Nov 2026)

- **No pattern was statistically significant in both periods** on either timeframe
  (0 of 112 pattern/horizon pairs on 5-min, 0 of 140 on 1-min; |t| > 2 required in both).
- Whether a pattern's direction in 2022–24 matched 2025–26 was a coin flip (55–56%).
- The exhaustive state grid (every Stochastic zone/cross x MACD side x MA side/slope combination)
  had a **negative** correlation between in-sample and out-of-sample results (−0.23 / −0.17):
  what worked before tended to reverse.
- Bearish signals more often preceded small *rises* than falls (mean reversion), but by under 1 basis point.
- The best hints, traded one at a time with a 0.2 bp per-side cost, earned $0.02–$0.10 per $1,000 trade
  ($54–$103 over 4 years per $1,000 traded), versus $929 for buying and holding SPY.

Conclusion: on SPY, these three indicators do not carry a scalping edge that survives costs.

## Tests

```bash
python3 -m pytest examples/spy-scalp-patterns/tests -v
```
