# SPY 30-Minute Opening Range Breakout (ORB) Backtest

A self-contained backtester for a classic opening-range-breakout day trade on SPY using 5-minute candles.

## Strategy rules (defaults)

| Rule | Value |
|---|---|
| Opening range | High / low of the first 30 minutes (09:30–10:00 ET, six 5-min candles) |
| Signal | First 5-min candle **closing** above the range high → long; closing below the range low → short |
| Trades per day | Max 1; no new entries after 15:30 ET |
| Entry | Close of the breakout candle (`--entry-mode next_open` to use the next candle's open) |
| Position size | Fixed **$1,000 per trade** (fractional shares), no compounding |
| Stop loss | **5% of the trade** (entry × 0.95 long / × 1.05 short), checked intrabar; gaps fill at the bar open |
| Trailing stop (optional) | `--stop-mode atr`: starts at entry ∓ `atr_mult` × ATR(14, 5-min bars) and ratchets up as price makes new highs (long) / down on new lows (short); never looser than the 5% stop |
| Take profit | **10%** of the trade by default (`--take-profit-pct N`, or `--no-target`) |
| Exit | Stop, target, or close of the 15:55 ET candle |
| Hold limit (optional) | `--max-hold-minutes 60` closes N minutes after entry; `--exit-time 11:00` closes at a clock time |
| Skip days (optional) | `--skip-fomc` sits out Fed decision days (built-in 2022–2026 calendar); `--skip-dates-file` for your own list (CPI, NFP, ...) |
| Range filter (optional) | `--max-or-width-rel 0.4` trades only when the opening range is ≤ 40% of the prior 10-day average daily range |

If a single bar touches both stop and target, the stop is assumed to fill first (conservative).

## Usage

```bash
pip install -r examples/spy-orb-backtest/requirements.txt

# Default: last 60 days of SPY 5-min bars from Yahoo Finance
python3 examples/spy-orb-backtest/orb_backtest.py --output-dir reports/

# Variants
python3 examples/spy-orb-backtest/orb_backtest.py --stop-mode atr --atr-mult 2   # ATR trailing stop
python3 examples/spy-orb-backtest/orb_backtest.py --stop-mode range      # stop at opposite side of range
python3 examples/spy-orb-backtest/orb_backtest.py --take-profit-pct 1.0  # tighter 1% target
python3 examples/spy-orb-backtest/orb_backtest.py --long-only --slippage-pct 0.01 --commission 0.5
python3 examples/spy-orb-backtest/orb_backtest.py --position-size 3000 --account-size 1000   # 3x leverage

# Longer history from your own CSV (timestamp, open, high, low, close[, volume]; naive times = ET)
python3 examples/spy-orb-backtest/orb_backtest.py --csv spy_5m.csv
```

Outputs go to `reports/spy_orb_backtest_<date>.md`, `.json`, and `_trades.csv`.

## Multi-year data (Alpaca, free)

```bash
export ALPACA_API_KEY=...  ALPACA_SECRET_KEY=...   # free paper account at alpaca.markets
python3 examples/spy-orb-backtest/fetch_alpaca_bars.py --symbol SPY --years 4 --out data/spy_5m.csv
python3 examples/spy-orb-backtest/orb_backtest.py --csv data/spy_5m.csv --stop-mode atr
```

## Walk-forward check

`walk_forward.py` searches 192 combinations of stop type, hold limit, FOMC skip, range filter and target.
For each test year it picks the best combination using only earlier years, then scores it on the unseen year.

```bash
python3 examples/spy-orb-backtest/walk_forward.py --csv data/spy_5m.csv --test-years 2024 2025 2026
```

## Data limitation

Yahoo Finance only serves ~60 days of 5-minute data, so the default run covers about 60 trades. That is too
small a sample to draw conclusions from. For a meaningful test, supply a multi-year 5-min CSV (from FMP, Alpaca,
Polygon, etc.) through `--csv`.

## Tests

```bash
python3 -m pytest examples/spy-orb-backtest/tests -v
```

_Hypothetical results only. Not investment advice._
