def calculate_metrics(trades):
    total=len(trades);wins=[t for t in trades if t['r_multiple']>0];losses=[t for t in trades if t['r_multiple']<0];gp=sum(t['r_multiple'] for t in wins);gl=abs(sum(t['r_multiple'] for t in losses));pf=gp/gl if gl else (float('inf') if gp else 0.0);equity=peak=dd=0.0;max_loss_streak=loss_streak=0
    for t in trades:
        r=t['r_multiple'];equity+=r;peak=max(peak,equity);dd=max(dd,peak-equity)
        if r<0:loss_streak+=1;max_loss_streak=max(max_loss_streak,loss_streak)
        else:loss_streak=0
    buy=[t for t in trades if t.get('signal')=='BUY'];sell=[t for t in trades if t.get('signal')=='SELL']
    def wr(xs):return sum(1 for t in xs if t['r_multiple']>0)/len(xs)*100 if xs else 0.0
    return {'total':total,'wins':len(wins),'losses':len(losses),'win_rate':len(wins)/total*100 if total else 0.0,'profit_factor':pf,'net_r':sum(t['r_multiple'] for t in trades),'expectancy_r':sum(t['r_multiple'] for t in trades)/total if total else 0.0,'max_drawdown_r':dd,'max_loss_streak':max_loss_streak,'buy_total':len(buy),'buy_win_rate':wr(buy),'sell_total':len(sell),'sell_win_rate':wr(sell)}
