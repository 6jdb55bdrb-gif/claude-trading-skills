# SuperTrend long-only (spot). Parameters come from config "rsys_supertrend",
# generated from config/settings.yaml. The indicator is shared with the other engines
# (rsys.indicators) so jesse / nautilus / FinRL see identical signals.
import logging

from freqtrade.strategy import IStrategy
from pandas import DataFrame
from rsys.indicators import supertrend

logger = logging.getLogger(__name__)


class SuperTrendStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = False
    minimal_roi = {"0": 100}  # exits come from the SuperTrend flip or the stoploss
    stoploss = -0.10  # overridden by config (risk.stoploss_pct)
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count = 50

    def bot_start(self, **kwargs) -> None:
        params = self.config.get("rsys_supertrend", {})
        self.atr_period = int(params.get("atr_period", 10))
        self.multiplier = float(params.get("multiplier", 3.0))
        if not params.get("params_confirmed", False):
            logger.warning(
                "SuperTrend is running with PLACEHOLDER parameters %s/%s",
                self.atr_period,
                self.multiplier,
            )

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        st = supertrend(dataframe, self.atr_period, self.multiplier)
        dataframe["supertrend"] = st["supertrend"]
        dataframe["st_direction"] = st["st_direction"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        flip_up = (dataframe["st_direction"] == 1) & (dataframe["st_direction"].shift(1) == -1)
        dataframe.loc[flip_up & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        flip_down = (dataframe["st_direction"] == -1) & (dataframe["st_direction"].shift(1) == 1)
        dataframe.loc[flip_down, "exit_long"] = 1
        return dataframe
