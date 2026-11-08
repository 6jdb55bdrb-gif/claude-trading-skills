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

# Longer history from your own CSV (timestamp, open, high, low, close[, volume]; naive times = ET)
python3 examples/spy-orb-backtest/orb_backtest.py --csv spy_5m.csv
```

Outputs go to `reports/spy_orb_backtest_<date>.md`, `.json`, and `_trades.csv`.

## Data limitation

Yahoo Finance only serves ~60 days of 5-minute data, so the default run covers about 60 trades. That is too
small a sample to draw conclusions from. For a meaningful test, supply a multi-year 5-min CSV (from FMP, Alpaca,
Polygon, etc.) through `--csv`.

## Tests

```bash
python3 -m pytest examples/spy-orb-backtest/tests -v
```

_Hypothetical results only. Not investment advice._
