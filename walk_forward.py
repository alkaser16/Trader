from backtest.lab import walk_forward
r=walk_forward('XAU/USD','15m',90,30,10)
print(f"Windows: {r['windows']} | Positive: {r['positive_windows']}/{r['windows']} ({r['positive_pct']:.1f}%)")
for i,x in enumerate(r['results'],1):print(f"Window {i}: score={x['score']} trades={x['total']} win={x['win_rate']:.1f}% PF={x['profit_factor']:.2f} net={x['net_r']:.2f}R")
