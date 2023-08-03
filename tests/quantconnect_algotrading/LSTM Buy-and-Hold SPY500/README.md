# LSTM Buy And Hold SPY Algorithm

The LSTMBuyAndHoldSPY algorithm is a simple buy-and-hold strategy applied to the SP500 index (represented by the SPY ETF). The algorithm buys and holds SPY until the price rises or lowers up to a certain amount. Afterward, it stays in cash for one month before buying and holding again.

The algorithm utilizes a Long Short-Term Memory (LSTM) model to make one-step ahead forecasts for SPY's future prices and dynamically adjusts trading positions based on forecasted price movements.

## Strategy Description
The algorithm follows the following steps:

1. **Initialization:** The algorithm sets the start and end dates for the backtest, defines the initial cash amount for simulation, and sets basic algorithm settings such as the entry price, time period (31 days), and the next entry time (initially set to the start date).

2. **Brokerage Model:** The algorithm specifies the brokerage model as InteractiveBrokersBrokerage and sets the account type to Margin, enabling the use of leverage if needed.

3. **Adding Security:** The algorithm adds the SPY (SP500 ETF) as an equity security with a daily resolution. It also sets the data normalization mode to Raw, meaning no modifications will be made to the asset price (e.g., dividends will be paid in cash).

4. **LSTM Forecast:** The algorithm defines a function to make forecasts using a Keras LSTM model. It prepares historical data of close prices as input sequences, reshapes the data for LSTM, builds and trains the model, and finally, makes one-step ahead forecasts along with confidence intervals.

5. **Entry Logic:** If the current time is equal to or beyond the next entry time and the algorithm is not already invested, it checks whether it's time to invest based on the forecasted price movements from the LSTM model. If the conditions are met, the algorithm buys SPY by setting holdings to 1, records the entry price, and sets the next entry time for the next period (31 days).

6. **Exit Logic:** If the algorithm is already invested, it collects historical close prices for the past 3 months and makes forecasts using the LSTM model. It updates the lower and upper targets based on the forecasted confidence intervals. If the current price is outside the forecast bounds, the algorithm sells all SPY holdings and goes to cash. After the sale, it sets the next entry time for the next period.

7. **Portfolio Logging:** At the end of each OnData event, the algorithm logs the current portfolio value.

## Requirements
The algorithm uses the QuantConnect API and requires the following libraries and dependencies:

- `numpy`
- `datetime`
- `statsmodels`
- `keras`

## Usage
To use the LSTM Buy And Hold SPY algorithm, simply copy the entire code and save it into a Python file with a ".py" extension. Then, execute the script in a QuantConnect environment or platform for backtesting or live trading with SPY data.

## Backtesting

![](../../../img/ARIMA_Long_Short_V1.png)

## Disclaimer
This algorithm is for educational and informational purposes only. It is not intended as financial or investment advice. Trading in financial markets involves risk, and past performance does not guarantee future results. Always conduct your research and consult with a qualified financial advisor before making any investment decisions.