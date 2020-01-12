import pandas as pd
import datetime as dt
from ta import volatility, trend, momentum
import ta

df = pd.read_pickle('./EURUSD').reset_index().rename({'date': 'datetime'}, axis=1).set_index('datetime')

df = df[df.index.date > dt.datetime(2019, 9, 1).date()]


#RSI_K, RSI_D, sma200, fut10, atr, exch

df['exch'] = 1

df['atr_'] = (df.high - df.low)
df['atr'] = df['atr_'].rolling(200).mean()

df['sma200'] = df.close.rolling(200).mean()
df['fut10'] = df.close.shift(10) / df.close
df['RSI_K'] = ta.momentum.rsi(df.close, 14).round(0)
df['RSI_D'] = df['RSI_K'].rolling(5).mean().round(0)



pd.to_pickle(df, './EURUSD_ind')

print(df.tail())


