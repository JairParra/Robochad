# general imports 
import numpy as np 
from datetime import timedelta
import statsmodels.api as sm
from keras.models import Sequential
from keras.layers import LSTM, Dense

# framewoirk imports 
from AlgorithmImports import QCAlgorithm
from AlgorithmImports import Resolution, DataNormalizationMode 
from AlgorithmImports import BrokerageName, AccountType
from AlgorithmImports import Slice
# endregion

class LSTMBuyAndHoldSPY(QCAlgorithm):
    """
    Simple buy and hold algorithm on the SP500. The bot will buy and hold SP500 
    until the price rises or lowers up to a certain amount. Afterward, stay in cash for one month 
    until we buy and hold again.
    
    This algorithm uses an LSTM model to make one-step ahead forecasts for SPY's future prices 
    and dynamically adjust trading positions based on forecasted price movements.
    """

    def Initialize(self):

        self.SetTimeZone('America/Montreal')

        self.Log("Initialize()..") # useful for debugging 


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

        self.upper_target = 0  # Initialize with default value
        self.lower_target = 0  # Initialize with default value

    def ForecastLSTM(self, history_data):
        """
        Make forecasts using the Keras LSTM model.

        Arguments:
            history_data (list): Historical data of close prices.

        Returns:
            forecast (float): One-step ahead forecast.
            confidence_80 (tuple): Tuple containing the lower and upper 80% confidence bounds.
            confidence_95 (tuple): Tuple containing the lower and upper 95% confidence bounds.
        """
        def prepare_data(data, n_steps):
            X, y = [], []
            for i in range(len(data) - n_steps):
                X.append(data[i:i+n_steps])
                y.append(data[i+n_steps])
            return np.array(X), np.array(y).reshape(-1, 1)

        n_steps = 30  # Number of time steps to use as input sequence
        X, y = prepare_data(history_data, n_steps)

        # Reshape data for LSTM (samples, time steps, features)
        X = X.reshape(X.shape[0], X.shape[1], 1)

        # Build and train the LSTM model
        model = Sequential()
        model.add(LSTM(30, activation='relu', input_shape=(n_steps, 1), return_sequences=True))  # Extra LSTM layer
        model.add(LSTM(30, activation='relu'))  # Original LSTM layer
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mse')
        model.fit(X, y, epochs=50, verbose=0)

        # Make a one-step ahead forecast using the last n_steps data
        last_n_steps = np.array(history_data[-n_steps:]).reshape(1, n_steps, 1)
        forecast = model.predict(last_n_steps)[0][0]

        # Compute the confidence intervals for 80% and 95% confidence levels
        stderr = np.std(y[-10:])  # Use the last 10 true values as the standard error
        conf_int_80 = forecast - 1.28 * stderr, forecast + 1.28 * stderr  # 80% confidence bounds (1.28 for z-score of 1.28)
        conf_int_95 = forecast - 1.96 * stderr, forecast + 1.96 * stderr  # 95% confidence bounds (1.96 for z-score of 1.96)

        return forecast, conf_int_80, conf_int_95

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

        # Implement the exit process with LSTM forecast bounds
        else:

            # Collect historical close prices for the past 3 months
            history_data = self.History(self.spy, 90, Resolution.Daily)['close'].tolist()

            # Make forecasts using LSTM model, and extract confidence bounds 
            forecast, confidence_80, confidence_95 = self.ForecastLSTM(history_data)

            # Update lower and upper targets accordingly 
            self.lower_target = confidence_95[0]
            self.upper_target = confidence_80[1]

            # Check if the current price is outside the ARIMA forecast bounds
            if price < self.lower_target or price > self.upper_target:
                # Liquidate all positions in the portfolio
                self.Liquidate() 
                self.Log(f"SELL SPY @{price}. Upper Target: {self.upper_target}, Lower Target: {self.lower_target}")

                # Make sure that for the next 30 days we'll stay in cash 
                self.nextEntryTime = self.Time + self.period 


        # Log portfolio value
        self.Log(f"Current Portfolio value: {self.Portfolio.TotalPortfolioValue}")