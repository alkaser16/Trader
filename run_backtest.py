from backtest.lab import run_backtest
from backtest.report import print_report
for tf in ('5m','15m','30m','1h','4h'):
    try:
        m,_=run_backtest('XAU/USD',tf,30,75,12,4,True,1.8);print_report(m,'XAU/USD',tf)
    except Exception as e:print(f'ERROR {tf}: {e}')
