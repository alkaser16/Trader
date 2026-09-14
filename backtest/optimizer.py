import json,os,random,time
from data.market import get_historical_candles
from backtest.engine import backtest_for_timeframe
from backtest.metrics import calculate_metrics

TF_TO_INTERVAL={'5m':'5min','15m':'15min','30m':'30min','1h':'1h','4h':'4h'}
TF_DAILY={'5m':288,'15m':96,'30m':48,'1h':24,'4h':6}
MAX_HOLD={'5m':96,'15m':64,'30m':48,'1h':24,'4h':12}
CACHE={}
BEST_PATH=os.path.join(os.path.dirname(os.path.dirname(__file__)),'data','optimizer_best.json')

def _bars(tf,days): return int(TF_DAILY[tf]*days*1.12)
def _candles(symbol,tf,days):
    key=(symbol,tf,days)
    if key not in CACHE:CACHE[key]=get_historical_candles(symbol,TF_TO_INTERVAL[tf],_bars(tf,days))
    return CACHE[key]

def _run(candles,tf,p):
    return calculate_metrics(backtest_for_timeframe(candles,TF_TO_INTERVAL[tf],risk_reward=p['min_rr'],minimum_score=p['min_score'],minimum_edge=p['min_edge'],min_confirmations=p['min_confirmations'],strict=p['strict_mode'],max_hold=MAX_HOLD[tf],atr_mult=p['atr_sl_multiplier'],swing_lookback=p['swing_lookback']))

def _quality(m):
    # Robustness-first objective: require enough trades and positive expectancy/PF.
    if m['total']<10:return -999.0
    pf=min(m['profit_factor'],5.0) if m['profit_factor']!=float('inf') else 5.0
    dd=max(m['max_drawdown_r'],0.01)
    return m['expectancy_r']*100 + (pf-1)*10 + min(m['win_rate'],75)*0.10 - dd*0.8 + min(m['total'],300)*0.01

def parameter_space():
    # Deliberately bounded to avoid overfitting and excessive API/CPU cost.
    return {'min_score':[65,70,75,80,85],'min_edge':[8,12,16,20],'min_confirmations':[3,4,5],'strict_mode':[True,False],'min_rr':[1.6,1.8,2.0,2.2],'atr_sl_multiplier':[1.0,1.25,1.5],'swing_lookback':[20,25,30]}

def sample_configs(limit=160,seed=44):
    rng=random.Random(seed); sp=parameter_space(); seen=set();out=[]
    while len(out)<limit:
        p={k:rng.choice(v) for k,v in sp.items()}; key=tuple(sorted(p.items()))
        if key in seen:continue
        seen.add(key);out.append(p)
    return out

def optimize(symbol='XAU/USD',timeframe='15m',days=60,limit=160):
    candles=_candles(symbol,timeframe,days); rows=[]
    for i,p in enumerate(sample_configs(limit),1):
        m=_run(candles,timeframe,p); rows.append({'params':p,'objective':_quality(m),**m})
    viable=[x for x in rows if x['objective']>-900]
    viable.sort(key=lambda x:(x['objective'],x['profit_factor'],x['expectancy_r']),reverse=True)
    best=viable[0] if viable else None
    result={'version':'V4.5','symbol':symbol,'timeframe':timeframe,'days':days,'tested':len(rows),'best':best,'top':viable[:10],'created_at':time.time()}
    os.makedirs(os.path.dirname(BEST_PATH),exist_ok=True)
    with open(BEST_PATH,'w',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return result

def out_of_sample(symbol='XAU/USD',timeframe='15m',days=90,train_ratio=.8,limit=160):
    candles=_candles(symbol,timeframe,days); split=max(260,int(len(candles)*train_ratio)); train=candles[:split]; test=candles[split:]
    rows=[]
    for p in sample_configs(limit):
        m=_run(train,timeframe,p); rows.append((m,p))
    viable=[x for x in rows if _quality(x[0])>-900]; viable.sort(key=lambda x:_quality(x[0]),reverse=True)
    if not viable:return {'ok':False,'reason':'لا توجد تركيبات ذات عدد صفقات كافٍ في التدريب.','candles':len(candles)}
    train_m,bestp=viable[0]; test_m=_run(test,timeframe,bestp) if len(test)>=260 else calculate_metrics([])
    return {'ok':len(test)>=260,'symbol':symbol,'timeframe':timeframe,'days':days,'train_candles':len(train),'test_candles':len(test),'params':bestp,'train':train_m,'test':test_m}

def walk_forward_auto(symbol='XAU/USD',timeframe='15m',days=120,train_days=30,test_days=10,limit=100):
    candles=_candles(symbol,timeframe,days); bpd=TF_DAILY[timeframe]; train=max(260,int(train_days*bpd)); test=int(test_days*bpd); results=[]; start=train
    while start+test<=len(candles):
        train_c=candles[start-train:start];test_c=candles[start:start+test]; rows=[]
        for p in sample_configs(limit,seed=start):rows.append((_run(train_c,timeframe,p),p))
        viable=[x for x in rows if _quality(x[0])>-900]
        if viable:
            viable.sort(key=lambda x:_quality(x[0]),reverse=True); tm,bp=viable[0]; xm=_run(test_c,timeframe,bp)
            results.append({'best_params':bp,'train':tm,'test':xm})
        start+=test
    positive=sum(1 for x in results if x['test']['expectancy_r']>0)
    return {'symbol':symbol,'timeframe':timeframe,'windows':len(results),'positive_windows':positive,'positive_pct':positive/len(results)*100 if results else 0,'results':results}

def load_best():
    try:
        with open(BEST_PATH,'r',encoding='utf-8') as f:return json.load(f)
    except Exception:return None
