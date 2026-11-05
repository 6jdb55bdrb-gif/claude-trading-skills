# ICT Silver Bullet: Mechanical Rule Set

This file turns the discretionary ICT (Inner Circle Trader) Silver Bullet idea
into rules a backtester can check without judgement calls. Every rule below
maps to a field in `SilverBulletParams` (`scripts/silver_bullet.py`).

## 1. Time Windows (America/New_York, DST-aware)

| Window | NY time | Notes |
|---|---|---|
| `london` | 03:00–04:00 | London open. Not available for cash ETFs (SPY/QQQ premarket starts 04:00), so use futures (ES/NQ) or 24h assets (BTC). |
| `am` | 10:00–11:00 | The "classic" Silver Bullet, 30 min after the US cash open. |
| `pm` | 14:00–15:00 | Afternoon session. |

A bar is inside the window when its **open time** is inside `[start, end)`.
The setup **and** the entry fill must both happen inside the window. Any open
position is closed `flat_minutes_after_window` minutes after the window ends
(default 60).

## 2. Draw on Liquidity: Pre-Window Reference Range

- Reference range = all bars in `[window_start − ref_lookback_minutes, window_start − sweep_lead_minutes)` (defaults: 120 and 30 min, so 08:00–09:30 for the AM window).
- `ref_high` = buy-side liquidity (resting buy stops above the highs).
- `ref_low` = sell-side liquidity (resting sell stops below the lows).
- Only data from before the window is used, so these levels have no look-ahead.

## 3. Liquidity Sweep (`require_sweep`, default on)

- The sweep zone starts `sweep_lead_minutes` before the window (default 30), so the 09:30 cash-open run on pre-market liquidity counts for the AM window.
- **Bullish:** in the sweep zone or the window, price trades **below** `ref_low`. The lowest low after that point is the sweep extreme.
- **Bearish:** in the sweep zone or the window, price trades **above** `ref_high`.
- The sweep must happen on or before the displacement candle.

## 4. Displacement + Fair Value Gap

On three consecutive candles `c1, c2, c3` (with `c3` in the window and `c2` at
or after the window start):

- **Bullish FVG:** `low(c3) > high(c1)`. The gap is `[high(c1), low(c3)]`.
- **Bearish FVG:** `high(c3) < low(c1)`. The gap is `[high(c3), low(c1)]`.
- The gap height must be at least `min_fvg_atr × ATR(14)` (default 0.10).
- **Displacement:** the body of `c2` must be at least `displacement_atr × ATR` (default 0.5) in the direction of the trade.

## 5. Market Structure Shift (`require_mss`, default on)

- **Bullish:** `max(close(c2), close(c3))` is above the highest high of the `mss_lookback_bars` (default 5) bars before the sweep bar. The run on sell-side liquidity has reversed through the last swing high.
- **Bearish:** the mirror of the bullish rule.

## 6. Entry

- `entry_mode = edge` (default): limit order at the FVG's proximal edge (`low(c3)` for longs, `high(c3)` for shorts).
- `entry_mode = ce`: limit order at consequent encroachment (the FVG midpoint). This gives a better price but fewer fills.
- The order is live from the bar after `c3` until the window closes.
- The order is cancelled if price reaches the target before the entry fills.
- Fills are always at the limit price, with no price improvement on gaps.

## 7. Stop

- Longs: `min(sweep low, low(c1), low(c2)) − stop_buffer_atr × ATR`.
- Shorts: the mirror of the long rule.
- The setup is skipped if the risk is more than `max_risk_atr × ATR` (default 4).
- The setup is skipped if the round-trip cost is more than `max_cost_r` R (default 0.10). This removes 1m stops that are too tight for the instrument's fees.

## 7b. Optional Daily Bias (`bias_filter = sma`)

- Long setups are allowed only when the previous completed NY day closed above its `bias_sma_days` (20) daily SMA.
- Short setups are allowed only when it closed below.
- Days without enough history are skipped.

## 8. Target

- `target_mode = liquidity` (default): the opposing pre-window liquidity (`ref_high` for longs, `ref_low` for shorts). The setup is skipped unless the reward is at least `min_rr` R (default 1.5). This is the ICT "draw on liquidity".
- `target_mode = rr`: a fixed `rr_target` R.

## 9. Trade Management and Fill Conservatism

- Each window takes at most one filled trade.
- If a bar touches both the stop and the target, the stop is assumed to be hit first.
- On the fill bar, only the stop is evaluated.
- After the fill bar, a gap through the stop exits at the open. A gap through the target also exits at the open.
- The position is time-exited at the close of the last bar before the flat deadline.
- Costs are `cost_bps` per side (defaults: Binance 2 bp, Yahoo futures/ETFs 0.5 bp) and are converted into R.

## 10. Robustness Protocol

A configuration is only called an edge when all of the following hold:

1. There are at least 30 trades.
2. Expectancy is above 0 R after costs, **and** the bootstrap 95% CI lower bound is above 0.
3. Both chronological halves have positive expectancy (a stability / walk-forward check).
4. At least 60% of the 96-config sensitivity grid (entry mode × target × MSS on/off × displacement threshold × bias filter) is profitable. The edge must not depend on one parameter choice.

Anything weaker is labelled `POSITIVE_UNCONFIRMED`, `UNSTABLE`, `NO_EDGE` or
`INSUFFICIENT_SAMPLE`.

## Known Discretionary Elements Not Modelled

- Higher-timeframe bias beyond the simple SMA filter. ICT traders read it from the daily/4H draw on liquidity.
- News-day filters (CPI, FOMC). You can add these by dropping dates before calling `run_backtest`.
- Prior-day high/low and session-level liquidity pools as targets. Only the pre-window range is used.
- Partial profit-taking and break-even stops.
