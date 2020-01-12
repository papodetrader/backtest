'''
'''
__author__ = "Alon horesh, Alpha Over Beta"
__credits__ = __author__
__license__ = "Restricted"
__version__ = "0.0.4"
__maintainer__ = __author__
__email__ = "alon@alphaoverbeta.net"
__status__ = "Production"

import sys
import pandas as pd
import backtrader as bt
import datetime as dt
# noinspection PyUnresolvedReferences
import ffn

import os

bet = 100
capital = 100000.0
stop_x = 2
target_x = 5
duration = 120
entry_time = (dt.datetime(2019, 1, 1, 9, 0).time(), dt.datetime(2019, 1, 1, 15, 0).time())
exit_time = (dt.datetime(2019, 1, 1, 12, 4).time(), dt.datetime(2019, 1, 1, 18, 4).time())
comissao = 4
strat_name = 'V1'
description = [3,5,7]


class BtStrategy1(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        BET = bet,
        stop_atr_multiplier = stop_x,
        target_atr_multiplier = target_x,
    )

    def __init__(self,df):
        '''
        backtrader init function
        :param last_date: the last trade date in historical quotes
        :param optimize: true for optimization cycle
        '''
        self.df = df
        self.df['entry_price']=0
        self.df['exit_price']=0
        self.df['pnl']=0
        self.df['size']=0
        self.df['stop']=0
        self.df['target']=0

        self.equity_list = []

    def notify_trade(self, trade):
        current_time = self.datas[0].datetime.datetime(0)
        if trade.isopen:
            self.df.loc[self.df.index==current_time, 'entry_price'] = trade.data.open[0]
            self.df.loc[self.df.index==current_time, 'size'] = trade.size
            self.df.loc[self.df.index==current_time, 'stop'] = self.stop_loss
            self.df.loc[self.df.index==current_time, 'target'] = self.take_profit
            self.df.loc[self.df.index==current_time, 'stop_time'] = self.stop_time
            self.trade_size = trade.size
            self.entry_price = trade.data.open[0]

        if trade.isclosed:
            self.df.loc[self.df.index==current_time, 'exit_price'] = self.exit_price
            self.df.loc[self.df.index==current_time, 'pnl'] = self.trade_size * (self.exit_price - self.entry_price)

    def next(self):
        '''
        backtrade runs each cycle
        '''
        current_time = self.datas[0].datetime.datetime(0)

        todays_quote = self.df.loc[current_time]

        size = int((self.p.BET * todays_quote['exch']) / (self.p.stop_atr_multiplier * todays_quote['atr']))


        cond_long = (
                    ((todays_quote.name.time() >= entry_time[0] and todays_quote.name.time() <= exit_time[0]) or
                    (todays_quote.name.time() >= entry_time[1] and todays_quote.name.time() <= exit_time[1]))

                    and todays_quote['RSI_K'] > todays_quote['RSI_D'] #3
                    and todays_quote['close'] > todays_quote['sma200'] #5
                    and todays_quote['fut10'] > 1 #7 

                    )

        cond_short = (
                    ((todays_quote.name.time() >= entry_time[0] and todays_quote.name.time() <= exit_time[0]) or
                    (todays_quote.name.time() >= entry_time[1] and todays_quote.name.time() <= exit_time[1]))

                    and todays_quote['RSI_K'] < todays_quote['RSI_D'] #3
                    and todays_quote['close'] < todays_quote['sma200'] #5
                    and todays_quote['fut10'] < 1 #7

                    )



        if self.position.size < 0 :
            if todays_quote['high'] > self.stop_loss:
                self.exit_price = todays_quote['high']
                self.close()
            elif todays_quote['low'] < self.take_profit:
                self.exit_price = self.take_profit
                self.close()
            elif todays_quote.name > self.stop_time:
                self.exit_price = todays_quote['close']
                self.close()

        if self.position.size > 0 :
            if todays_quote['high'] > self.take_profit:
                self.exit_price = self.take_profit
                self.close()
            elif todays_quote['low'] < self.stop_loss:
                self.exit_price = todays_quote['low']
                self.close()
            elif todays_quote.name > self.stop_time:
                self.exit_price = todays_quote['close']
                self.close()


        if not self.position.size: # a position is open
            
            if cond_long:

                self.buy(size=size)
                self.stop_loss = todays_quote['close']-(self.p.stop_atr_multiplier * todays_quote['atr'])
                self.take_profit = todays_quote['close']+(self.p.target_atr_multiplier * todays_quote['atr'])
                self.stop_time = todays_quote.name + dt.timedelta(minutes=duration)

            if cond_short:

                self.sell(size=size)
                self.stop_loss = todays_quote['close']+(self.p.stop_atr_multiplier * todays_quote['atr'])
                self.take_profit = todays_quote['close']-(self.p.target_atr_multiplier * todays_quote['atr'])
                self.stop_time = todays_quote.name + dt.timedelta(minutes=duration)


    def stop(self):
        '''
        backtrade end of cycle
        '''

        pd.to_pickle(self.df, f'./{self.df.asset.unique()[0]}_performance')
        self.df.to_csv('./performance.csv')

        db = self.df[self.df.pnl != 0]
        db['pnl'] = db['pnl'] / db['exch']
        df = pd.concat([self.df.iloc[0:1], db])['pnl']

        x = capital

        result = {}

        for i in df.iteritems():
            x = x + (i[1] - comissao) #comission entry-exit
            result.update({i[0]: {'equity': x}})

        equity = pd.DataFrame(result.values(), result.keys())
        equity.index = pd.to_datetime(equity.index)
        stats = equity['equity'].calc_stats()
        
        try:
            backtest = pd.read_pickle('./backtest')
        except:
            backtest = {}

        others_stats = {
            'QTY': len(db),
            'PROFIT_QTY': len(db[db.pnl > 0]),
            'LOST_QTY': len(db[db.pnl < 0]), 
            'PROFIT_%': len(db[db.pnl > 0]) / len(db),
            'PROFIT_AVG_$': sum(db[db.pnl > 0].pnl) / len(db[db.pnl > 0]),
            'LOST_AVG_$': sum(db[db.pnl < 0].pnl) / len(db[db.pnl < 0]),
            'Win_x_Lost': (sum(db[db.pnl > 0].pnl) / len(db[db.pnl > 0])) / sum(db[db.pnl < 0].pnl) / len(db[db.pnl < 0]),
            'Description': description,
            }

        others_stats = pd.DataFrame(others_stats.values(), others_stats.keys())

        backtest.update({f'{self.df.asset.unique()[0]}_{strat_name}': stats.stats.append(others_stats)})
        pd.to_pickle(backtest, './backtest')

        stats.display()
        print(len(df))


if __name__ == '__main__':

    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    # Create a data feed
    df = pd.read_pickle('./EURUSD_ind').dropna()

    df["datetime"] = pd.to_datetime(df.index)
    df = df.set_index("datetime")
    # df.drop(['time'], axis=1, inplace=True)
    bt_data = bt.feeds.PandasData(dataname=df, open='open', high='high', low='low',
                                close='close', openinterest=None)

    cerebro.adddata(bt_data)
    cerebro.addstrategy(BtStrategy1, df=df)  # Add the trading strategy
    cerebro.broker.setcommission(commission=0.0015)
    cerebro.broker.setcash(capital)
    thestrats = cerebro.run(maxcpus = 4)



