# general imports 
import numpy as np 
from datetime import timedelta
import statsmodels.api as sm
import itertools  

# framewoirk imports 
from AlgorithmImports import QCAlgorithm
from AlgorithmImports import Resolution, DataNormalizationMode 
from AlgorithmImports import BrokerageName, AccountType
from AlgorithmImports import Slice
# endregion

class LongShortARIMA(QCAlgorithm):
    """
    The Long-Short ARIMA Algorithm is a dynamic trading strategy that uses the 
    Autoregressive Integrated Moving Average (ARIMA) model to make long and 
    short sell decisions on tradeable securities based on price trends and 
    forecasted confidence bounds. The algorithm dynamically adjusts trading positions
    and sets take-profit and stop-loss thresholds based on the ARIMA forecast for
    the next 4 candles.
    """

    def Initialize(self):

        self.Log("Initialize()..") # useful for debugging 

        # Initialize backtesting parameters for strategy
        self.SetStartDate(2022, 1, 1) 
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


        ## NOTE: try this algorithm with different securities 
        # # add securities to algorithm
        # spy = self.AddEquity("SPY", Resolution.Daily) # lowest resolution: tick (avoid!) 

        # # specify data normalization mode 
        # spy.SetDataNormalizationMode(DataNormalizationMode.Raw) # no mods to asset price at all, div paid cash

        # # store security Symbol (more info) inside class 
        # self.spy = spy.Symbol 

        # Add securities to algorithm
        nvda = self.AddEquity("NVDA", Resolution.Daily) # lowest resolution: tick (avoid!) 

        # Specify data normalization mode 
        nvda.SetDataNormalizationMode(DataNormalizationMode.Raw) # no mods to asset price at all, div paid cash

        # Store security Symbol (more info) inside class 
        self.nvda = nvda.Symbol 


    def AssessTrend(self, data, lookback=21):
        """
        Assess the trend of the stock based on the past 21-candles SMA and the current stock price.

        Arguments:
            - data (list): List of historical close prices.
            - lookback (int): Number of candles to use for SMA calculation.

        Returns:
            - trend (str): "uptrend" if the current price is above the SMA, "downtrend" otherwise.
        """
        current_price = data[-1]
        sma = np.mean(data[-lookback:])
        if current_price > sma:
            return "uptrend"
        else:
            return "downtrend"

    def FindBestARIMA(self, data):
        """
        Find the best ARIMA(p, d, q) model based on the BIC criterion.

        Arguments:
            - data (list): List of historical close prices.

        Returns:
            - best_arima_model (ARIMA): The best ARIMA(p, d, q) model.
        """
        best_bic = np.inf
        best_arima_model = None

        p_values = range(3)
        d_values = range(2)
        q_values = range(3)

        # Create all possible combinations of p, d, and q values
        all_combinations = list(itertools.product(p_values, d_values, q_values))

        for p, d, q in all_combinations:
            try:
                arima_model = sm.tsa.ARIMA(data, order=(p, d, q)).fit()
                bic = arima_model.bic
                if bic < best_bic:
                    best_bic = bic
                    best_arima_model = arima_model
            except:
                continue

        return best_arima_model



    def PerformARIMAForecast(self, history_data):
        """
        Perform ARIMA(p, d, q) forecast on the Close price for the next 4 candles using the most optimal ARIMA model.

        Arguments:
            - history_data (list): Historical data of close prices.

        Returns:
            - forecast (list): List containing the forecasts for the next 4 candles.
            - confidence_80 (tuple): Tuple containing the lower and upper 80% confidence bounds for the forecasts.
        """

        # Find the best ARIMA model based on the BIC criterion
        arima_model = self.FindBestARIMA(history_data)

        # Make a 4-step ahead forecast
        forecast = arima_model.forecast(steps=4)

        # Compute the confidence intervals for 80% confidence level
        stderr = np.sqrt(arima_model.predict(start=arima_model.nobs-1,
                                             end=arima_model.nobs+3,
                                             dynamic=False).var())
        confidence_80 = forecast - 1.28 * stderr, forecast + 1.28 * stderr  # 80% confidence bounds (1.28 for z-score of 1.28)

        return forecast, confidence_80

    def OnData(self, data: Slice):
        """
        This method is called every time the algorithm receives new data.
        That is, every time a bar data reaches its end-time, or a tick occurs.

        Arguments: 
            - data (Slice): Slice object keyed by symbol containing the stock data
        """

        # Check if requested data does already exist 
        # e.g. NVDA is very actively traded, but other securities might not 
        if not self.nvda in data: 
            return

        # Save current price (day before) of NVDA
        price = data.Bars[self.nvda].Close

        # Check if our bot has already invested 
        if not self.Portfolio.Invested: 

            # Check if it's time to invest, e.g.
            # if current time is greater than or equal to the next entry time
            if self.nextEntryTime <= self.Time:

                # If yes, we want to buy as much NVDA as we can
                self.SetHoldings(self.nvda, 1)  # Allocate 100% of portfolio to NVDA
                self.Log("BUY NVDA @" + str(price))  # Record for debugging 

                # Set entry price (not exact, as market price may deviate from order placed time)
                self.entryPrice = price

        # Implement the exit process with ARIMA forecast bounds
        else:

            # Collect historical close prices for the past 14 candles
            history_data = self.History(self.nvda, 90, Resolution.Daily)['close'].tolist()

            # Assess the trend (uptrend or downtrend)
            trend = self.AssessTrend(history_data)

            # Perform ARIMA forecast for the next 4 candles
            forecast, confidence_80 = self.PerformARIMAForecast(history_data)

            # Set take profit and stop loss thresholds based on the 80% confidence bounds of the 4th day of the forecast
            if trend == "uptrend":
                take_profit = forecast[3] + (confidence_80[1][3] - forecast[3])  # 80% confidence upper bound
                stop_loss = forecast[3] - (forecast[3] - confidence_80[0][3])  # 80% confidence lower bound
            else:  # downtrend
                take_profit = forecast[3] - (forecast[3] - confidence_80[0][3])  # 80% confidence lower bound
                stop_loss = forecast[3] + (confidence_80[1][3] - forecast[3])  # 80% confidence upper bound

            # Check if the current price is outside the take profit or stop loss thresholds
            if trend == "uptrend" and (price >= take_profit or price <= stop_loss):
                # Long the stock today
                self.SetHoldings(self.nvda, 1)
                self.Log(f"Long NVDA @ {price}. Take Profit: {take_profit}, Stop Loss: {stop_loss}")
            elif trend == "downtrend" and (price <= take_profit or price >= stop_loss):
                # Short the stock today
                self.SetHoldings(self.nvda, -1)
                self.Log(f"Short NVDA @ {price}. Take Profit: {take_profit}, Stop Loss: {stop_loss}")

            # Set the next entry time (stay in cash for 30 days)
            self.nextEntryTime = self.Time + self.period

        # Log portfolio value
        self.Log(f"Current Portfolio value: {self.Portfolio.TotalPortfolioValue}")