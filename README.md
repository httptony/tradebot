# Crypto Trend Bot + Market Trend Board

EMA crossover + RSI filter + volatility-based stops. Long-only spot. Runs as a **backtest** or a
**paper trader** (live prices, fake money), and comes with the **Market Trend Board** dashboard,
which runs on your own computer with no Claude needed. It can't place real orders yet, and that's on purpose.

## Dashboard (runs off Claude)
```bash
python main.py paper --dashboard   # bot + dashboard together (recommended)
python main.py dashboard           # dashboard only
```
Then open **http://localhost:8765** in any browser. The page lives in `dashboard/index.html`.
Prices come from Yahoo Finance through the bot's small built-in server (`bot/server.py`), and the page
refreshes every minute. The Trade bot panel shows the paper balance, any open trade, the trade history,
and whether the bot agrees with the board on Bitcoin.

To open it from your phone on the same Wi-Fi, set `dashboard: host: 0.0.0.0` in config.yaml and browse
to `http://<your computer's IP>:8765`. Only do this on a network you trust: there's no login.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Use
```bash
python main.py backtest --demo     # offline smoke test on synthetic data
python main.py backtest            # real history from the exchange in config.yaml
python main.py optimize            # tests EMA combos on 70% of the data, then checks the best one on the other 30%
python main.py paper               # paper trade live (Ctrl+C or create a file named STOP to halt)
python main.py paper --reset       # start a fresh paper account
python main.py paper --once        # one check, then exit (good for cron / Task Scheduler)
```

Outputs:
- `reports/` has the trades CSV, the equity curve CSV, and a chart PNG for each backtest
- `logs/` has the run logs, plus `paper_trades.csv`
- `state/paper_state.json` stores the paper balance and any open position, so a restart picks up where it left off

## Strategy
| | Rule |
|---|---|
| Entry | EMA20 crosses above EMA50 on a finished candle, price is above EMA200, RSI is between 50 and 70 |
| Exit | EMA20 crosses below EMA50 |
| Candles | 15 minutes (`timeframe: 15m`), the same as the dashboard default. Switch to `1d` for slower, fewer trades |
| Stop | entry − 2×ATR, then trails at 3×ATR below the high once the trade is in profit |
| Take profit | entry + 4×ATR |
| Size | sized so that hitting the stop loses 1% of equity, with a cap of 95% of the balance |

Signals use closed candles only and fill at the next open. The backtest includes fees (0.1%) and slippage (0.05%).
Every setting lives in `config.yaml`.

## Safety
- Daily loss limit: paper mode stops opening new trades after a 5% loss in one day (UTC)
- Kill switch: create a file named `STOP` in the project folder
- Network errors: it retries with backoff instead of crashing

## Before going live
1. Backtest across several years and symbols, including at least one bear market.
2. Make sure `optimize` gives similar results in-sample and out-of-sample.
3. Paper trade for a few weeks and check that the results look like the backtest.
4. Only then add live order execution, using API keys **without withdrawal permission**.

Not financial advice. Most simple trend strategies lose to buy-and-hold in strong bull markets.
In return they're meant to cut drawdowns.

## A note on 15-minute trading
More candles means more trades, so fees matter much more. With 0.1% per buy and per sell, a round trip costs 0.2%,
and a typical 15-minute target is only around 1%. Run `python main.py backtest` first: the results include fees,
so you can see whether the strategy still makes money after them on 15-minute candles.

## What the backtests showed (October 2026, real Yahoo prices, fees included)
| Setup | Result |
|---|---|
| These rules on 15-minute BTC candles, last 30 days | −4.9% (1 win in 15 trades; fees were over half the loss) |
| These rules on daily BTC candles, 2017 to 2026 | about 0% (14 trades in 9.5 years) |
| "Stay in the trend" daily rule (close > EMA200 and EMA20 > EMA50), BTC since 2020 | +47%/year, worst drop −38% |
| Fast trend daily rule (close > EMA100 and EMA10 > EMA30), BTC since 2020 | +61%/year, worst drop −33% |
| Three common 5-minute scalping strategies, last 30 days | −5.5% to −55% |

Short timeframes lose to fees and noise; slow trend-following was the only setup with an edge.
Past results don't predict future ones. Not financial advice.
