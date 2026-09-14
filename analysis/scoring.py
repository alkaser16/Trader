def calculate_score(direction, structure, current, higher, sr_score, smc, strict=True):
    buy=sell=0; rb=[]; rs=[]
    def add(side,points,text,confirm=True):
        nonlocal buy,sell
        if side=='BUY': buy+=points; rb.append(text)
        elif side=='SELL': sell+=points; rs.append(text)
    if higher.get('price') is not None and higher.get('ema200') is not None:
        if higher['price']>higher['ema200']: add('BUY',12,'السياق الأعلى فوق EMA200')
        elif higher['price']<higher['ema200']: add('SELL',12,'السياق الأعلى تحت EMA200')
    if higher.get('ema50') and higher.get('ema200'):
        if higher['ema50']>higher['ema200']: add('BUY',8,'EMA50 أعلى من EMA200')
        elif higher['ema50']<higher['ema200']: add('SELL',8,'EMA50 أدنى من EMA200')
    if 'BULLISH' in structure: add('BUY',15,f'هيكل {structure}')
    elif 'BEARISH' in structure: add('SELL',15,f'هيكل {structure}')
    r=current.get('rsi')
    if r is not None:
        if 52<=r<=68: add('BUY',7,f'RSI داعم للشراء {r:.1f}')
        elif 32<=r<=48: add('SELL',7,f'RSI داعم للبيع {r:.1f}')
    if current.get('macd') is not None and current.get('macd_signal') is not None:
        if current['macd']>current['macd_signal']: add('BUY',7,'MACD إيجابي')
        elif current['macd']<current['macd_signal']: add('SELL',7,'MACD سلبي')
    if current.get('ema20') and current.get('ema50'):
        if current['ema20']>current['ema50']: add('BUY',6,'EMA20/50 صاعد')
        elif current['ema20']<current['ema50']: add('SELL',6,'EMA20/50 هابط')
    ad=current.get('adx'); pdi=current.get('plus_di'); mdi=current.get('minus_di')
    if ad is not None and ad>=20:
        if pdi is not None and mdi is not None and pdi>mdi: add('BUY',6,f'ADX {ad:.1f} مع +DI')
        elif pdi is not None and mdi is not None and mdi>pdi: add('SELL',6,f'ADX {ad:.1f} مع -DI')
    if sr_score>0: add('BUY',5,'السعر قريب من دعم')
    elif sr_score<0: add('SELL',5,'السعر قريب من مقاومة')
    sweep=smc.get('liquidity_sweep')
    if sweep=='SELL_SIDE_SWEEP': add('BUY',10,'سحب سيولة أسفل القيعان')
    elif sweep=='BUY_SIDE_SWEEP': add('SELL',10,'سحب سيولة أعلى القمم')
    if smc.get('fvg_bias')=='BULLISH': add('BUY',6,'FVG صاعد قريب')
    elif smc.get('fvg_bias')=='BEARISH': add('SELL',6,'FVG هابط قريب')
    if smc.get('ob_bias')=='BULLISH': add('BUY',6,'Order Block صاعد قريب')
    elif smc.get('ob_bias')=='BEARISH': add('SELL',6,'Order Block هابط قريب')
    if smc.get('displacement')=='BULLISH': add('BUY',5,'Displacement صاعد')
    elif smc.get('displacement')=='BEARISH': add('SELL',5,'Displacement هابط')
    if direction=='BULLISH': add('BUY',5,'اتجاه HTF صاعد')
    elif direction=='BEARISH': add('SELL',5,'اتجاه HTF هابط')
    if buy==sell: return {'signal':'NO_TRADE','score':0,'buy_score':buy,'sell_score':sell,'edge':0,'confirmations':0,'reasons':[]}
    signal='BUY' if buy>sell else 'SELL'; best=max(buy,sell); other=min(buy,sell); reasons=rb if signal=='BUY' else rs
    return {'signal':signal,'score':min(best,100),'buy_score':buy,'sell_score':sell,'edge':best-other,'confirmations':len(reasons),'reasons':reasons}
