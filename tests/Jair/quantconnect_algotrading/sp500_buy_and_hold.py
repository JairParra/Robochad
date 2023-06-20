# general imports 
import numpy
from datetime import timedelta

# framewoirk imports 
from AlgorithmImports import QCAlgorithm
from AlgorithmImports import Resolution, DataNormalizationMode 
from AlgorithmImports import BrokerageName, AccountType
from AlgorithmImports import Slice
# endregion

class CryingYellowZebra(QCAlgorithm):
    """
    Simple buy and hold algorithm on the SP500. The bot will buy and hold sp500 
    until the price rices or lowers up to a certain amount.
    Thereafter, stay in cash for one month until we buy and hold again. 
    """

    def Initialize(self):

        # Initialize backtesting parameters for strategy
        self.SetStartDate(2020, 9, 23) 
        self.SetEndDate(2021, 1, 1)
        self.SetCash(100000) 

        # Initialize basic algorithm settings 
        self.entryPrice = 0
        self.period = timedelta(31) 
        self.nextEntryTime = self.Time # since we want to start investing right away

        # add securities to algorithm
        spy = self.AddEquity("SPY", Resolution.Daily)

        # specify data normalization mode 
        spy.SetDataNormalizationMode(DataNormalizationMode.Raw)

        # set algorithm benchmark (will generate a chart at backtesting time)
        self.SetBenchmark("SPY")

        # store security Symbol (more info) inside class 
        self.spy = spy.Symbol 

        # specify Brokerage model (for accounting) 
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage,
                                AccountType.Margin) # allow to use leverage, else specify CASH



    def OnData(self, data: Slice):

        # check if data exists 
        if not self.spy in data: 
            return

        # save current price (day before) of the spy500 
        price = data.Bars[self.spy].Close 
        # price = self.Securities[self.spy].Close 

        # check portfolio status to start investing 
        if not self.Portfolio.Invested: 
            # check if time is valid 
            if self.nextEntryTime <= self.Time:
                ## Option 1 
                # buy as much SPY as we can 
                # self.MarketOrder(self.spy, self.PorfolioCash / price)

                ## Option 2 
                # specify holding proportion for the spy 
                self.SetHoldings(self.spy, 1) # 100% to spy 
                self.Log("BUY SPY @" + str(price)) # record for debugging 

                # set entry price (not exact, as mkt price may deviate from order placed time)
                self.entryPrice = price

        # stay in cash for 30 days
        elif self.entryPrice * 1.1 < price or self.entryPrice * 0.9 > price: 
            # liquidate all positions in portfolio 
            self.Liquidate() 
            self.Log("SELL SPY @" + str(price)) 

            # make sure that for the next 30 days we'll stay in cash 
            self.nextEntryTime = self.Time + self.period 