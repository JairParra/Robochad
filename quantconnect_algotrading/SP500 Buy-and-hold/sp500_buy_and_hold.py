# general imports 
import numpy
from datetime import timedelta

# framewoirk imports 
from AlgorithmImports import QCAlgorithm
from AlgorithmImports import Resolution, DataNormalizationMode 
from AlgorithmImports import BrokerageName, AccountType
from AlgorithmImports import Slice
# endregion

class BuyAndHoldSPY(QCAlgorithm):
    """
    Simple buy and hold algorithm on the SP500. The bot will buy and hold sp500 
    until the price rices or lowers up to a certain amount.
    Thereafter, stay in cash for one month until we buy and hold again. 
    """

    def Initialize(self):

        self.Log("Initialize()..") # useful for debugging 

        # # Initialize backtesting parameters for strategy
        # self.SetStartDate(2020, 9, 23) 
        # self.SetEndDate(2021, 1, 1)
        # self.SetCash(100000)  

        # Initialize backtesting parameters for strategy
        self.SetStartDate(2023, 1, 1) 
        self.SetEndDate(2023, 7, 1)
        self.SetCash(2000) # simulation money 

        # Initialize basic algorithm settings 
        self.entryPrice = 0 # track entry price of our SPY position
        self.period = timedelta(31) # timeframe of 31 days
        self.nextEntryTime = self.Time # tracks when we should we re-entre along / want to strat investing right away (cur time)

        # set algorithm benchmark (will generate a chart at backtesting time)
        self.SetBenchmark("SPY")
        self.Log(f"Current benchmark name: {self.Benchmark}")

        # specify Brokerage model (for accounting) 
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, # read about this broker? 
                               AccountType.Margin) # allow to use leverage, else specify CASH

        # add securities to algorithm
        spy = self.AddEquity("SPY", Resolution.Daily) # lowest resolution: tick (avoid!) 

        # specify data normalization mode 
        spy.SetDataNormalizationMode(DataNormalizationMode.Raw) # no mods to asset price at all, div paid cash

        # store security Symbol (more info) inside class 
        self.spy = spy.Symbol 



    def OnData(self, data: Slice):
        """
        This method is called everytime the algorithm receives new data.
        That is, everytime a bar data reaches its end-time, or a tick occurrs.

        Arguments: 
            - data (Slice): Slice object keyed by symbol containing the stock data
        """

        # check if requested data does already exist 
        # e.g. the spy500 is very actively traded, but other securities might not 
        if not self.spy in data: 
            return

        # save current price (day before) of the spy500 
        price = data.Bars[self.spy].Close  # index security + access Bars attribute Close
        # price = self.Securities[self.spy].Close 

        # check if our bot has already invested 
        # (note) could also access a specific security only
        if not self.Portfolio.Invested: 

            # check if it's time to invest, e.g.
            # if current time is geq to the next entry time
            if self.nextEntryTime <= self.Time:

                # If yes, we want to buy as much SPY as we can

                ## Option 1 
                # buy as much SPY as we can 
                # self.MarketOrder(self.spy, self.PorfolioCash / price)

                ## Option 2 
                # specify holding proportion for the spy 
                self.SetHoldings(self.spy, 1) # allocate 100% of portf to spy 
                self.Log("BUY SPY @" + str(price)) # record for debugging 

                # set entry price (not exact, as mkt price may deviate from order placed time)
                self.entryPrice = price

        # implement the exit process 
        # reached when portf is currently invested; and price is below or above by 10% 
        elif self.entryPrice * 1.1 < price or self.entryPrice * 0.95 > price: 
            # liquidate all positions in portfolio 
            self.Liquidate() 
            self.Log("SELL SPY @" + str(price)) 

            # make sure that for the next 30 days we'll stay in cash 
            self.nextEntryTime = self.Time + self.period 


        # Log portfolio value
        self.Log(f"Current Portfolio value: {self.Portfolio.TotalPortfolioValue}")