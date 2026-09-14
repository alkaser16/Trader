def print_report(m,symbol,timeframe):
 print(f'\n{symbol} | {timeframe}\n'+'-'*70)
 for k,v in [('Trades',m['total']),('Win rate',f"{m['win_rate']:.2f}%"),('Profit factor',f"{m['profit_factor']:.2f}"),('Net R',f"{m['net_r']:.2f}"),('Expectancy',f"{m['expectancy_r']:.3f} R"),('Max DD',f"{m['max_drawdown_r']:.2f} R"),('Max loss streak',m['max_loss_streak'])]:print(f'{k}: {v}')
