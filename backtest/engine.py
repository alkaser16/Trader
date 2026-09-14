from datetime import datetime, timezone
from analysis.indicators import ema,rsi,atr,macd,adx,slope
from analysis.structure import detect_structure,liquidity_sweep,liquidity_levels,fair_value_gaps,order_blocks,displacement,find_swing_highs,find_swing_lows
from analysis.support_resistance import get_support_resistance,evaluate_sr
from analysis.scoring import calculate_score

TF_MIN={'1min':1,'5min':5,'15min':15,'30min':30,'1h':60,'4h':240,'1day':1440}
HIGHER={'1min':'5min','5min':'15min','15min':'1h','30min':'1h','1h':'4h','4h':'1day','1day':'1day'}

def _dt(v):
    if isinstance(v,datetime): return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00')); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except: return None

def aggregate(candles,target_minutes):
    out=[]; groups={}
    for c in candles:
        d=_dt(c['datetime'])
        if not d: continue
        epoch=int(d.timestamp()); bucket=(epoch//(target_minutes*60))*(target_minutes*60)
        groups.setdefault(bucket,[]).append(c)
    for bucket,cs in sorted(groups.items()):
        cs=sorted(cs,key=lambda x:x['datetime'])
        out.append({'datetime':datetime.fromtimestamp(bucket,tz=timezone.utc).isoformat(),'open':cs[0]['open'],'high':max(x['high'] for x in cs),'low':min(x['low'] for x in cs),'close':cs[-1]['close']})
    return out

def _snap(candles):
    closes=[x['close'] for x in candles]; ml,ms,mh=macd(closes); av=atr(candles,14); ad,pdi,mdi=adx(candles,14)
    return {'candles':candles,'price':closes[-1],'ema20':ema(closes,20),'ema50':ema(closes,50),'ema200':ema(closes,200),'rsi':rsi(closes,14),'atr':av,'adx':ad,'plus_di':pdi,'minus_di':mdi,'macd':ml,'macd_signal':ms,'macd_hist':mh,'slope':slope(closes,5),'structure':detect_structure(candles)}

def _smc(cur):
    fvg=fair_value_gaps(cur['candles']);obs=order_blocks(cur['candles'],cur['atr']);price=cur['price'];av=cur['atr'] or 0
    def near(items,t):
        return bool(av) and any(x['type']==t and x['low']-av<=price<=x['high']+av for x in items[-8:])
    return {'liquidity_sweep':liquidity_sweep(cur['candles']),'liquidity':liquidity_levels(cur['candles']),'displacement':displacement(cur['candles'],cur['atr']),'fvg_bias':'BULLISH' if near(fvg,'BULLISH_FVG') else ('BEARISH' if near(fvg,'BEARISH_FVG') else 'NONE'),'ob_bias':'BULLISH' if near(obs,'BULLISH_OB') else ('BEARISH' if near(obs,'BEARISH_OB') else 'NONE')}

def _trade_levels(cur,signal,min_rr=1.8,atr_mult=1.25,swing_lookback=25):
    av=cur['atr'] or 0; price=cur['price']; recent=cur['candles'][-int(swing_lookback):]
    highs=[x[1] for x in find_swing_highs(recent)]; lows=[x[1] for x in find_swing_lows(recent)]
    if not av:return None
    if signal=='BUY':
        structural=min(lows) if lows else price-av*atr_mult; sl=min(price-av*atr_mult,structural-av*.08); risk=price-sl
        resistance=min([x for x in highs if x>price],default=None); tp1=price+risk; tp2=price+risk*min_rr; tp3=price+risk*max(3,min_rr*1.5)
        if resistance:
            if resistance<tp2:return None
            tp2=min(tp2,resistance-av*.10)
            if tp2<=price+risk*1.5:return None
            tp3=max(tp3,tp2+risk*.5)
    else:
        structural=max(highs) if highs else price+av*atr_mult; sl=max(price+av*atr_mult,structural+av*.08); risk=sl-price
        support=max([x for x in lows if x<price],default=None); tp1=price-risk; tp2=price-risk*min_rr; tp3=price-risk*max(3,min_rr*1.5)
        if support:
            if support>tp2:return None
            tp2=max(tp2,support+av*.10)
            if tp2>=price-risk*1.5:return None
            tp3=min(tp3,tp2-risk*.5)
    rr=abs(tp2-price)/abs(price-sl) if signal=='BUY' else abs(tp2-price)/abs(sl-price)
    if rr<min_rr:return None
    return {'stop_loss':sl,'tp1':tp1,'tp2':tp2,'tp3':tp3,'risk':abs(price-sl),'rr_tp2':rr}

def _signal_at(candles,index,timeframe,min_score,min_edge,min_confirm,strict,min_rr,atr_mult=1.25,swing_lookback=25):
    hist=candles[:index+1]
    if len(hist)<260:return None
    cur=_snap(hist); target=TF_MIN[timeframe]; htf_name=HIGHER[timeframe]; htf_minutes=TF_MIN[htf_name]
    if htf_minutes==target: higher=cur
    else:
        d=_dt(hist[-1]['datetime']); bucket=(int(d.timestamp())//(htf_minutes*60))*(htf_minutes*60) if d else 0
        htf_all=aggregate(hist,htf_minutes); higher=[x for x in htf_all if int(_dt(x['datetime']).timestamp())<bucket]
        if len(higher)<220:return None
        higher=_snap(higher)
    levels=get_support_resistance(hist); sr=evaluate_sr(cur['price'],cur['atr'],levels); smc=_smc(cur)
    direction='BULLISH' if higher['price']>higher['ema200'] else ('BEARISH' if higher['price']<higher['ema200'] else 'NEUTRAL')
    scored=calculate_score(direction,cur['structure'],cur,higher,sr['score'],smc,strict=strict)
    if scored['signal']=='NO_TRADE' or scored['score']<min_score or scored['edge']<min_edge or scored['confirmations']<min_confirm:return None
    levels_trade=_trade_levels(cur,scored['signal'],min_rr,atr_mult,swing_lookback)
    if not levels_trade:return None
    return {'signal':scored['signal'],'entry':cur['price'],'stop':levels_trade['stop_loss'],'target':levels_trade['tp2'],'r_target':min_rr,'score':scored['score'],'edge':scored['edge'],'confirmations':scored['confirmations'],'entry_index':index}

def backtest_for_timeframe(candles,timeframe='15min',risk_reward=1.8,minimum_score=75,minimum_edge=12,min_confirmations=4,strict=True,max_hold=288,atr_mult=1.25,swing_lookback=25):
    trades=[]; i=260
    while i<len(candles)-1:
        sig=_signal_at(candles,i,timeframe,minimum_score,minimum_edge,min_confirmations,strict,risk_reward,atr_mult,swing_lookback)
        if not sig:i+=1;continue
        exit_idx=None; outcome=None
        for j in range(i+1,min(len(candles),i+1+max_hold)):
            c=candles[j]
            sl_hit=c['low']<=sig['stop'] if sig['signal']=='BUY' else c['high']>=sig['stop']
            tp_hit=c['high']>=sig['target'] if sig['signal']=='BUY' else c['low']<=sig['target']
            if sl_hit: outcome=-1.0;exit_idx=j;break
            if tp_hit: outcome=sig['r_target'];exit_idx=j;break
        if outcome is None:break
        trades.append({**sig,'r_multiple':outcome,'exit_index':exit_idx}); i=exit_idx+1
    return trades

def backtest(candles,risk_reward=1.8,minimum_score=75,minimum_edge=12,min_confirmations=4,strict=True,min_rr=None,max_hold=288,atr_mult=1.25,swing_lookback=25):
    return backtest_for_timeframe(candles,'15min',risk_reward,minimum_score,minimum_edge,min_confirmations,strict,max_hold,atr_mult,swing_lookback)
