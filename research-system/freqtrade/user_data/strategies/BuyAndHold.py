# BASELINE: buy on the first candle, hold to the end. Used for every comparison.
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class BuyAndHold(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False
    minimal_roi = {"0": 100}  # never take profit
    stoploss = -0.99  # baseline is exempt from the stoploss rule
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        return dataframe
