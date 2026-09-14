def sma(values, period):
    if len(values) < period: return None
    return sum(values[-period:]) / period


def ema(values, period):
    if len(values) < period: return None
    k = 2.0 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]: value = price * k + value * (1-k)
    return value


def ema_series(values, period):
    if len(values) < period: return []
    k = 2.0 / (period + 1); value = sum(values[:period]) / period; result=[value]
    for price in values[period:]:
        value = price*k + value*(1-k); result.append(value)
    return result


def rsi(values, period=14):
    if len(values) < period+1: return None
    gains=[]; losses=[]
    for i in range(1,len(values)):
        d=values[i]-values[i-1]; gains.append(max(d,0.0)); losses.append(max(-d,0.0))
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    for i in range(period,len(gains)):
        ag=((ag*(period-1))+gains[i])/period; al=((al*(period-1))+losses[i])/period
    if al==0: return 100.0
    return 100.0-(100.0/(1.0+ag/al))


def atr(candles, period=14):
    if len(candles)<period+1: return None
    trs=[]
    for i in range(1,len(candles)):
        h,l=candles[i]['high'],candles[i]['low']; pc=candles[i-1]['close']
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    v=sum(trs[:period])/period
    for tr in trs[period:]: v=((v*(period-1))+tr)/period
    return v


def macd(values, fast=12, slow=26, signal=9):
    if len(values)<slow+signal: return None,None,None
    fs=ema_series(values,fast); ss=ema_series(values,slow); off=slow-fast
    ms=[a-b for a,b in zip(fs[off:],ss)]; sigs=ema_series(ms,signal)
    if not sigs: return None,None,None
    line=ms[-1]; sig=sigs[-1]; return line,sig,line-sig


def adx(candles, period=14):
    if len(candles)<period*2+1: return None,None,None
    tr=[]; plus=[]; minus=[]
    for i in range(1,len(candles)):
        c=candles[i]; p=candles[i-1]
        tr.append(max(c['high']-c['low'],abs(c['high']-p['close']),abs(c['low']-p['close'])))
        up=c['high']-p['high']; dn=p['low']-c['low']
        plus.append(up if up>dn and up>0 else 0.0); minus.append(dn if dn>up and dn>0 else 0.0)
    atrv=sum(tr[:period])/period; pv=sum(plus[:period])/period; mv=sum(minus[:period])/period
    dxs=[]
    def one():
        pdi=100*pv/atrv if atrv else 0; mdi=100*mv/atrv if atrv else 0
        dx=100*abs(pdi-mdi)/(pdi+mdi) if pdi+mdi else 0; return pdi,mdi,dx
    _,_,dx=one(); dxs.append(dx)
    for i in range(period,len(tr)):
        atrv=((atrv*(period-1))+tr[i])/period; pv=((pv*(period-1))+plus[i])/period; mv=((mv*(period-1))+minus[i])/period
        _,_,dx=one(); dxs.append(dx)
    if len(dxs)<period: return None,None,None
    av=sum(dxs[:period])/period
    for dx in dxs[period:]: av=((av*(period-1))+dx)/period
    pdi,mdi,_=one()
    return av,pdi,mdi


def slope(values, period=5):
    if len(values)<period+1: return 0.0
    return (values[-1]-values[-1-period])/period
