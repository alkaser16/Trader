from datetime import datetime, timezone
from data.market_cache import get_cached_candles
from analysis.indicators import ema,rsi,atr,macd,adx,slope
from analysis.structure import detect_structure,liquidity_sweep,liquidity_levels,fair_value_gaps,order_blocks,displacement,find_swing_highs,find_swing_lows
from analysis.support_resistance import get_support_resistance,evaluate_sr
from analysis.filters import market_quality
from analysis.scoring import calculate_score
from analysis.news import get_news_status
from config import *

TIMEFRAME_MAP={'1m':'1min','5m':'5min','15m':'15min','30m':'30min','1h':'1h','4h':'4h','1d':'1day'}
HIGHER_TIMEFRAME={'1m':'5m','5m':'15m','15m':'1h','30m':'1h','1h':'4h','4h':'1d','1d':'1d'}

def _session_state(settings):
    now=datetime.now(timezone.utc)
    if now.weekday()>=5:return False,False,f'عطلة نهاية الأسبوع | UTC {now:%H:%M}'
    enabled=bool(settings.get('session_filter_enabled',SESSION_FILTER_ENABLED))
    if not enabled:return True,False,f'مراقبة 24/5 | UTC {now:%H:%M}'
    start=int(settings.get('session_start_utc',SESSION_START_UTC)); end=int(settings.get('session_end_utc',SESSION_END_UTC))
    preferred=start<=now.hour<end if start<end else now.hour>=start or now.hour<end
    return True,preferred,f'الجلسة المفضلة UTC {start:02d}:00-{end:02d}:00 | الآن {now:%H:%M} UTC'

def analyze_timeframe(symbol,interval):
    candles=get_cached_candles(symbol,interval,360,ttl=45 if interval.endswith('min') else 120)
    if len(candles)<220:raise RuntimeError(f'بيانات غير كافية: {symbol} {interval} ({len(candles)})')
    closes=[c['close'] for c in candles]; ml,ms,mh=macd(closes); av=atr(candles,14); ad,pdi,mdi=adx(candles,14)
    return {'candles':candles,'price':closes[-1],'ema20':ema(closes,20),'ema50':ema(closes,50),'ema200':ema(closes,200),'rsi':rsi(closes,14),'atr':av,'adx':ad,'plus_di':pdi,'minus_di':mdi,'macd':ml,'macd_signal':ms,'macd_hist':mh,'slope':slope(closes,5),'structure':detect_structure(candles)}

def _near_bias(price,items,desired,atr_value):
    if not atr_value:return 'NONE'
    best=None
    for x in items[-8:]:
        if x['type']==desired and x['low']-atr_value<=price<=x['high']+atr_value:
            d=min(abs(price-x['low']),abs(price-x['high']))
            if best is None or d<best:best=d
    return desired if best is not None else 'NONE'

def _levels(cur,signal,settings):
    av=cur['atr'] or 0; price=cur['price']; look=int(settings.get('swing_lookback',SWING_LOOKBACK)); mult=float(settings.get('atr_sl_multiplier',ATR_SL_MULTIPLIER)); minrr=float(settings.get('min_rr',MIN_RR)); recent=cur['candles'][-look:]
    highs=[x[1] for x in find_swing_highs(recent)]; lows=[x[1] for x in find_swing_lows(recent)]
    if not av:return None
    if signal=='BUY':
        structural=min(lows) if lows else price-av*mult; sl=min(price-av*mult,structural-av*.08); risk=price-sl
        resistance=min([x for x in highs if x>price],default=None); tp1=price+risk; tp2=price+risk*minrr; tp3=price+risk*max(3,minrr*1.5)
        if resistance:
            if resistance<tp2:return None
            tp2=min(tp2,resistance-av*.10)
            if tp2<=price+risk*1.5:return None
            tp3=max(tp3,tp2+risk*.5)
    else:
        structural=max(highs) if highs else price+av*mult; sl=max(price+av*mult,structural+av*.08); risk=sl-price
        support=max([x for x in lows if x<price],default=None); tp1=price-risk; tp2=price-risk*minrr; tp3=price-risk*max(3,minrr*1.5)
        if support:
            if support>tp2:return None
            tp2=max(tp2,support+av*.10)
            if tp2>=price-risk*1.5:return None
            tp3=min(tp3,tp2-risk*.5)
    rr=abs(tp2-price)/abs(price-sl) if signal=='BUY' else abs(tp2-price)/abs(sl-price)
    return {'stop_loss':sl,'tp1':tp1,'tp2':tp2,'tp3':tp3,'risk':abs(price-sl) if signal=='BUY' else abs(sl-price),'rr_tp2':rr} if rr>=minrr else None

def analyze(symbol='XAU/USD',timeframe='15m',settings=None):
    settings=settings or {}; higher_tf=HIGHER_TIMEFRAME[timeframe]; cur=analyze_timeframe(symbol,TIMEFRAME_MAP[timeframe]); higher=analyze_timeframe(symbol,TIMEFRAME_MAP[higher_tf]); quality=market_quality(cur['candles'],cur['atr']); levels=get_support_resistance(cur['candles']); sr=evaluate_sr(cur['price'],cur['atr'],levels); news=get_news_status(symbol,settings)
    fvg=fair_value_gaps(cur['candles']); obs=order_blocks(cur['candles'],cur['atr']); smc={'liquidity_sweep':liquidity_sweep(cur['candles']),'liquidity':liquidity_levels(cur['candles']),'displacement':displacement(cur['candles'],cur['atr']),'fvg_bias':'BULLISH' if _near_bias(cur['price'],fvg,'BULLISH_FVG',cur['atr'])=='BULLISH_FVG' else ('BEARISH' if _near_bias(cur['price'],fvg,'BEARISH_FVG',cur['atr'])=='BEARISH_FVG' else 'NONE'),'ob_bias':'BULLISH' if _near_bias(cur['price'],obs,'BULLISH_OB',cur['atr'])=='BULLISH_OB' else ('BEARISH' if _near_bias(cur['price'],obs,'BEARISH_OB',cur['atr'])=='BEARISH_OB' else 'NONE'),'fvg':fvg[-4:],'order_blocks':obs[-4:]}
    direction='BULLISH' if higher['price']>higher['ema200'] else ('BEARISH' if higher['price']<higher['ema200'] else 'NEUTRAL')
    scored=calculate_score(direction,cur['structure'],cur,higher,sr['score'],smc,strict=bool(settings.get('strict_mode',STRICT_MODE))); signal=scored['signal']; reasons=list(scored['reasons']); market_open,preferred,session_text=_session_state(settings)
    min_score=int(settings.get('min_score',MIN_SCORE)); min_edge=int(settings.get('min_edge',MIN_EDGE)); min_conf=int(settings.get('min_confirmations',MIN_CONFIRMATIONS))
    eff_score=min(100,scored['score']+(SESSION_SCORE_BONUS if preferred else 0)); eff_edge=min(60,scored['edge']+(SESSION_EDGE_BONUS if preferred else 0))
    if not market_open:signal='NO_TRADE';reasons=['عطلة نهاية الأسبوع؛ المراقبة تعمل 24/5']
    elif not quality['allowed']:signal='NO_TRADE';reasons=[quality['reason']]
    elif news['blocked']:signal='NO_TRADE';reasons=[news['reason']]
    elif eff_score<min_score or eff_edge<min_edge or scored['confirmations']<min_conf:signal='NO_TRADE';reasons=[f'لم تكتمل الشروط: Score {eff_score}/{min_score}, Edge {eff_edge}/{min_edge}, Confirm {scored["confirmations"]}/{min_conf}']
    else:
        if not preferred:reasons.append('خارج الجلسة المفضلة؛ لا يوجد حظر زمني')
    levels_trade=_levels(cur,signal,{**settings,'atr_sl_multiplier':settings.get('atr_sl_multiplier',ATR_SL_MULTIPLIER),'swing_lookback':settings.get('swing_lookback',SWING_LOOKBACK)}) if signal in ('BUY','SELL') else None
    if signal in ('BUY','SELL') and not levels_trade:signal='NO_TRADE';reasons=['لا يوجد مسار مناسب إلى TP2 مع RR المطلوب قبل مستوى مهم']
    candle_time=cur['candles'][-1].get('datetime')
    return {'version':'V4.5','symbol':symbol,'timeframe':timeframe,'higher_timeframe':higher_tf,'signal':signal,'score':scored['score'],'buy_score':scored['buy_score'],'sell_score':scored['sell_score'],'edge':scored['edge'],'effective_score':eff_score,'effective_edge':eff_edge,'confirmations':scored['confirmations'],'price':cur['price'],'atr':cur['atr'],'stop_loss':levels_trade['stop_loss'] if levels_trade else None,'tp1':levels_trade['tp1'] if levels_trade else None,'tp2':levels_trade['tp2'] if levels_trade else None,'tp3':levels_trade['tp3'] if levels_trade else None,'risk':levels_trade['risk'] if levels_trade else None,'rr_tp2':levels_trade['rr_tp2'] if levels_trade else None,'trend':direction,'structure':cur['structure'],'higher_structure':higher['structure'],'rsi':cur['rsi'],'adx':cur['adx'],'plus_di':cur['plus_di'],'minus_di':cur['minus_di'],'macd_hist':cur['macd_hist'],'slope':cur['slope'],'support':sr['support'],'resistance':sr['resistance'],'market_status':quality['reason'],'news':news,'session':session_text,'preferred_session':preferred,'smc':smc,'reasons':reasons,'candle_time':candle_time}
