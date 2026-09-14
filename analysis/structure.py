def find_swing_highs(candles,left=2,right=2):
    out=[]
    for i in range(left,len(candles)-right):
        x=candles[i]['high']
        if all(candles[j]['high']<x for j in range(i-left,i)) and all(candles[j]['high']<=x for j in range(i+1,i+right+1)): out.append((i,x))
    return out


def find_swing_lows(candles,left=2,right=2):
    out=[]
    for i in range(left,len(candles)-right):
        x=candles[i]['low']
        if all(candles[j]['low']>x for j in range(i-left,i)) and all(candles[j]['low']>=x for j in range(i+1,i+right+1)): out.append((i,x))
    return out


def detect_structure(candles):
    if len(candles)<30: return 'NEUTRAL'
    highs=find_swing_highs(candles); lows=find_swing_lows(candles)
    if len(highs)<3 or len(lows)<3: return 'NEUTRAL'
    ph,lh=highs[-2][1],highs[-1][1]; pl,ll=lows[-2][1],lows[-1][1]; close=candles[-1]['close']
    if close>lh: return 'BULLISH_BOS'
    if close<ll: return 'BEARISH_BOS'
    if lh>ph and ll>pl: return 'BULLISH'
    if lh<ph and ll<pl: return 'BEARISH'
    if lh>ph and ll<pl: return 'BULLISH_CHOCH'
    if lh<ph and ll>pl: return 'BEARISH_CHOCH'
    return 'RANGE'


def liquidity_sweep(candles,lookback=20):
    if len(candles)<lookback+2: return 'NONE'
    prev=candles[-2]; recent=candles[-lookback-1:-2]; last=candles[-1]
    hi=max(x['high'] for x in recent); lo=min(x['low'] for x in recent)
    if prev['low']<lo and last['close']>lo: return 'SELL_SIDE_SWEEP'
    if prev['high']>hi and last['close']<hi: return 'BUY_SIDE_SWEEP'
    return 'NONE'


def liquidity_levels(candles,tolerance=0.0008,lookback=80):
    c=candles[-lookback:]; highs=find_swing_highs(c); lows=find_swing_lows(c)
    eqh=[]; eql=[]
    for i,a in enumerate(highs):
        for b in highs[i+1:]:
            if abs(a[1]-b[1])/max(abs(a[1]),1e-9)<=tolerance: eqh.append((a[1]+b[1])/2)
    for i,a in enumerate(lows):
        for b in lows[i+1:]:
            if abs(a[1]-b[1])/max(abs(a[1]),1e-9)<=tolerance: eql.append((a[1]+b[1])/2)
    return {'equal_highs':eqh[-5:],'equal_lows':eql[-5:]}


def fair_value_gaps(candles,max_items=12):
    gaps=[]
    for i in range(2,len(candles)):
        a,c=candles[i-2],candles[i]
        if c['low']>a['high']: gaps.append({'type':'BULLISH_FVG','low':a['high'],'high':c['low'],'index':i})
        elif c['high']<a['low']: gaps.append({'type':'BEARISH_FVG','low':c['high'],'high':a['low'],'index':i})
    return gaps[-max_items:]


def order_blocks(candles,atr_value,lookback=50):
    if not atr_value: return []
    blocks=[]; start=max(1,len(candles)-lookback)
    for i in range(start,len(candles)-2):
        c,n=candles[i],candles[i+1]; body=abs(c['close']-c['open']); impulse=abs(n['close']-c['close'])
        if body<=atr_value*.8 and impulse>=atr_value*1.2:
            if n['close']>c['close']: blocks.append({'type':'BULLISH_OB','low':c['low'],'high':max(c['open'],c['close']),'index':i})
            else: blocks.append({'type':'BEARISH_OB','low':min(c['open'],c['close']),'high':c['high'],'index':i})
    return blocks[-10:]


def displacement(candles,atr_value):
    if not atr_value or len(candles)<3: return 'NONE'
    c=candles[-1]; body=abs(c['close']-c['open'])
    if body<atr_value*1.2: return 'NONE'
    return 'BULLISH' if c['close']>c['open'] else 'BEARISH'
