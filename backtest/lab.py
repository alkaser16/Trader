from data.market import get_historical_candles
from backtest.engine import backtest_for_timeframe
from backtest.metrics import calculate_metrics
from backtest.optimizer import optimize,out_of_sample,walk_forward_auto
TF_TO_INTERVAL={'5m':'5min','15m':'15min','30m':'30min','1h':'1h','4h':'4h'}
TF_DAILY={'5m':288,'15m':96,'30m':48,'1h':24,'4h':6}
MAX_HOLD={'5m':96,'15m':64,'30m':48,'1h':24,'4h':12}
def _bars(tf,days):return int(TF_DAILY[tf]*days*1.12)
def run_backtest(symbol='XAU/USD',timeframe='15m',days=30,min_score=75,min_edge=12,min_confirm=4,strict=True,min_rr=1.8):
 c=get_historical_candles(symbol,TF_TO_INTERVAL[timeframe],_bars(timeframe,days));t=backtest_for_timeframe(c,TF_TO_INTERVAL[timeframe],risk_reward=min_rr,minimum_score=min_score,minimum_edge=min_edge,min_confirmations=min_confirm,strict=strict,max_hold=MAX_HOLD[timeframe]);m=calculate_metrics(t);m.update(candles=len(c),days_requested=days);return m,t
def optimize_scores(symbol='XAU/USD',timeframe='15m',days=30,scores=None,min_edge=12,min_confirm=4,strict=True,min_rr=1.8):
 if scores is None:scores=[60,65,70,75,80,85,90]
 c=get_historical_candles(symbol,TF_TO_INTERVAL[timeframe],_bars(timeframe,days));rows=[]
 for score in scores:
  t=backtest_for_timeframe(c,TF_TO_INTERVAL[timeframe],risk_reward=min_rr,minimum_score=score,minimum_edge=min_edge,min_confirmations=min_confirm,strict=strict,max_hold=MAX_HOLD[timeframe]);rows.append({'score':score,**calculate_metrics(t)})
 viable=[r for r in rows if r['total']>=10];best=max(viable,key=lambda r:(r['expectancy_r'],r['profit_factor'],r['win_rate'])) if viable else None;return rows,best,len(c)
def walk_forward(symbol='XAU/USD',timeframe='15m',days=90,train_days=30,test_days=10,scores=None,min_edge=12,min_confirm=4,strict=True,min_rr=1.8):
 r=walk_forward_auto(symbol,timeframe,days,train_days,test_days,80);return {'windows':r['windows'],'positive_windows':r['positive_windows'],'positive_pct':r['positive_pct'],'results':[{'score':x['best_params']['min_score'],**x['test']} for x in r['results']]}
