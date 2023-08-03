# general imports 
import numpy
from datetime import timedelta

# framewoirk imports 
from AlgorithmImports import QCAlgorithm
from AlgorithmImports import Resolution, DataNormalizationMode 
from AlgorithmImports import BrokerageName, AccountType
from AlgorithmImports import Slice
# endregion

class BuyAndHoldAlgorithm(QCAlgorithm):

    def Initialize(self):
        # Initialize backtesting parameters for strategy
        self.SetStartDate(2023, 4, 1)
        self.SetEndDate(2023, 7, 1)
        self.SetCash(2000) # simulation money

        # Initialize basic algorithm settings
        self.entryPrice = 0 # track entry price of our SPY position
        self.period = timedelta(31) # timeframe of 31 days
        self.nextEntryTime = self.Time # tracks when we should re-enter or start investing right away (current time)

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
        self.Log(f"SPY symbol: {self.spy}")

        # Set the indicators and moving average
        self.atr = self.ATR(self.spy, 14, Resolution.Daily)
        self.rsi = self.RSI(self.spy, 14, Resolution.Daily)
        self.sma = self.SMA(self.spy, 14, Resolution.Daily)

    def OnData(self, data):
        # Check if we reached the next entry time
        if self.Time >= self.nextEntryTime:
            spy = self.Securities["SPY"]

            if not self.Portfolio.Invested:
                # Check if we are on a 14-candle upward trend using the moving average
                if self.sma.IsReady and spy.Close > self.sma.Current.Value:
                    # Calculate the stop loss and take profit levels based on ATR and RSI
                    atrValue = self.atr.Current.Value
                    rsiValue = self.rsi.Current.Value

                    stopLoss = spy.Close - 1 * atrValue
                    takeProfit = spy.Close + 2 * atrValue

                    # Check if the risk-reward ratio meets the 1:2 criteria
                    if (takeProfit - spy.Close) >= 2 * (spy.Close - stopLoss):
                        # If the criteria is met, buy SPY
                        self.SetHoldings("SPY", 1)
                        self.entryPrice = spy.Close
                        self.nextEntryTime = self.Time + self.period
                        self.Log(f"Bought SPY at {self.entryPrice}. Stop Loss: {stopLoss}, Take Profit: {takeProfit}")

            else: 
                # If already invested, check if the price hit the stop loss or take profit level
                stopLoss = self.entryPrice - 1 * self.atr.Current.Value
                takeProfit = self.entryPrice + 2 * self.atr.Current.Value

                if spy.Close <= stopLoss or spy.Close >= takeProfit:
                    # If price hits stop loss or take profit, sell SPY and go to cash
                    self.Liquidate()
                    self.nextEntryTime = self.Time + self.period
                    self.Log(f"Sold SPY at {spy.Close}. Entered cash.")

        # Log portfolio value
        self.Log(f"Portfolio value: {self.Portfolio.TotalPortfolioValue}")

