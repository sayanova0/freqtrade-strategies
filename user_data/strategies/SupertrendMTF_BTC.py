from datetime import datetime
from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair
from technical.indicators import supertrend


class SupertrendMTF_BTC(IStrategy):
    timeframe = "1m"
    informative_timeframe = "5m"
    startup_candle_count = 210
    can_short = False
    process_only_new_candles = True
    max_open_trades = 1

    stoploss = -0.003
    minimal_roi = {"0": 0.002}

    trailing_stop = True
    trailing_stop_positive = 0.0015
    trailing_stop_positive_offset = 0.0030
    trailing_only_offset_is_reached = True

    def informative_pairs(self):
        return [("BTC/USDT", self.informative_timeframe)]

    def _indicators_5m(self, df: DataFrame) -> DataFrame:
        st = supertrend(df, period=10, multiplier=3.0)
        df["stx_5m"] = st["STX"]
        df["buy5m_event"] = ((df["stx_5m"] == 1) & (df["stx_5m"].shift(1) != 1)).astype(int)
        return df

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        if not pair.startswith("BTC/USDT"):
            df["enter_long"] = 0
            df["exit_long"] = 0
            return df

        inf_tf = self.informative_timeframe
        informative = self.dp.get_pair_dataframe(pair="BTC/USDT", timeframe=inf_tf)
        informative = self._indicators_5m(informative)

        df = merge_informative_pair(df, informative, self.timeframe, inf_tf, ffill=True)

        df["buy_trigger"] = ((df["buy5m_event_5m"].fillna(0) == 1) &
                             (df["buy5m_event_5m"].shift(1).fillna(0) == 0)).astype(int)

        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        df["enter_long"] = 0

        if pair.startswith("BTC/USDT"):
            df.loc[
                (df["buy_trigger"] == 1),
                "enter_long"
            ] = 1

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df["exit_long"] = 0
        if "stx_5m" in df.columns:
            df.loc[(df["stx_5m"] == -1), "exit_long"] = 1
        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str, **kwargs) -> float:
        return float(min(10, max_leverage))
