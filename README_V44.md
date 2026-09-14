# GoldBot V4.4

V4.4 adds a robustness-oriented automatic optimizer on top of V4.3.

## What it does
- Auto Optimizer searches bounded combinations of Score, Edge, confirmations, Strict, RR, ATR SL multiplier and swing lookback.
- Out-of-Sample (OOS) splits data into training and unseen test data.
- Walk-Forward Auto repeatedly optimizes on a past window and tests the selected configuration on the next unseen window.
- Best configuration is saved to `data/optimizer_best.json`.
- `💾 تطبيق الأفضل` applies only the saved parameters to the bot settings; it does not place trades.
- Existing monitoring remains analysis-only and does not execute orders.

## Telegram
- `/menu`
- `/test` = Backtest
- `/opt` = Auto Optimizer
- Strategy Lab contains Backtest, Score Lab, Walk-Forward and OOS.

## Important
Optimizer results are historical. They are not a guarantee of future performance. Do not choose a configuration solely by highest win rate; inspect trade count, profit factor, expectancy, drawdown and OOS/WF stability.

## Installation
```bash
cd ~/gold
unzip -o ~/storage/downloads/goldbot_v4_4_full.zip -d ~/gold
rm -rf __pycache__ analysis/__pycache__ bot/__pycache__ backtest/__pycache__ data/__pycache__
python -m compileall -q .
python main.py
```
Do not replace your `.env` with the `.env.example` file.
