from backtest.lab import optimize_scores
for tf in ('5m','15m','30m','1h','4h'):
 try:
  rows,best,n=optimize_scores('XAU/USD',tf,30)
  print('\n',tf,'candles=',n)
  for r in rows:print(r['score'],r['total'],f"{r['win_rate']:.1f}%",f"PF {r['profit_factor']:.2f}",f"Exp {r['expectancy_r']:.3f}R",f"DD {r['max_drawdown_r']:.2f}R")
  print('BEST=',best['score'] if best else None)
 except Exception as e:print('ERROR',tf,e)
