import threading
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup
from config import FINNHUB_API_KEY,NEWS_ENABLED,NEWS_FAIL_CLOSED,NEWS_BLOCK_MINUTES_BEFORE,NEWS_BLOCK_MINUTES_AFTER,NEWS_CACHE_SECONDS,NEWS_PROVIDER,NEWS_GENERAL_ENABLED,NEWS_RECENT_MINUTES,REQUEST_TIMEOUT

CACHE={'time':0.0,'events':[],'general':[],'error':None,'provider':None,'economic_ok':False,'general_ok':False}; LOCK=threading.Lock()
SYMBOL_CURRENCIES={'XAU/USD':{'USD'}}
GOLD_KEYWORDS=('gold','xau','federal reserve','fed','fomc','powell','inflation','cpi','pce','payroll','nfp','employment','unemployment','interest rate','rate decision','treasury','yield','dollar','usd','geopolitical','war','sanction','oil','crude','middle east','china')

def _parse_dt(v):
    if not v:return None
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00')); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception: pass
    try:
        d=parsedate_to_datetime(str(v)); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:return None

def _fetch_finnhub_economic():
    if not FINNHUB_API_KEY: raise RuntimeError('FINNHUB_API_KEY غير موجود')
    now=datetime.now(timezone.utc); params={'from':now.date().isoformat(),'to':(now.date()+timedelta(days=3)).isoformat(),'token':FINNHUB_API_KEY}
    r=requests.get('https://finnhub.io/api/v1/calendar/economic',params=params,timeout=REQUEST_TIMEOUT)
    if r.status_code==401: raise RuntimeError('Finnhub رفض مفتاح API (401 Unauthorized)')
    r.raise_for_status(); data=r.json(); out=[]
    for e in data.get('economicCalendar',[]):
        dt=_parse_dt(e.get('time') or e.get('date')); 
        if not dt: continue
        impact=str(e.get('impact') or e.get('importance') or '').lower(); level='HIGH' if impact in {'3','high','high impact'} else ('MEDIUM' if impact in {'2','medium','med'} else 'LOW')
        cur=str(e.get('country') or e.get('currency') or '').upper(); title=str(e.get('event') or e.get('indicator') or 'Economic event')
        out.append({'time':dt,'currency':cur,'impact':level,'title':title,'source':'Finnhub'})
    return out

def _fetch_finnhub_general():
    if not FINNHUB_API_KEY: raise RuntimeError('FINNHUB_API_KEY غير موجود')
    r=requests.get('https://finnhub.io/api/v1/news',params={'category':'general','token':FINNHUB_API_KEY},timeout=REQUEST_TIMEOUT)
    if r.status_code==401: raise RuntimeError('Finnhub رفض مفتاح API للأخبار العامة (401)')
    r.raise_for_status(); data=r.json() if isinstance(r.json(),list) else []; out=[]
    for x in data:
        dt=_parse_dt(x.get('datetime') and datetime.fromtimestamp(float(x['datetime']),tz=timezone.utc).isoformat())
        title=str(x.get('headline') or x.get('summary') or '')
        text=(title+' '+str(x.get('summary') or '')).lower()
        if dt and any(k in text for k in GOLD_KEYWORDS): out.append({'time':dt,'title':title[:220],'source':'Finnhub News'})
    return out

def _fetch_forexfactory():
    headers={'User-Agent':'Mozilla/5.0 GoldBot V4.5'}; last=None
    for url in ('https://www.forexfactory.com/calendar?day=today','https://www.forexfactory.com/calendar/rss'):
        try:
            r=requests.get(url,headers=headers,timeout=REQUEST_TIMEOUT); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser'); out=[]
            for row in soup.select('tr.calendar__row,tr.calendar_row,tr[data-event-id]'):
                raw=' '.join(row.stripped_strings); cur=next((c for c in ('USD','EUR','GBP','JPY','AUD','CAD','CHF','NZD') if c in raw),'')
                if not cur: continue
                low=raw.lower(); impact='HIGH' if 'high impact' in low or 'red' in low else ('MEDIUM' if 'medium' in low or 'orange' in low else 'LOW')
                rawdt=row.get('data-event-datetime') or row.get('data-timestamp'); dt=None
                if rawdt:
                    try:
                        ts=float(rawdt); ts=ts/1000 if ts>10_000_000_000 else ts; dt=datetime.fromtimestamp(ts,tz=timezone.utc)
                    except Exception: dt=_parse_dt(rawdt)
                if dt: out.append({'time':dt,'currency':cur,'impact':impact,'title':raw[:180],'source':'ForexFactory'})
            if out:return out
        except Exception as e:last=e
    raise RuntimeError(f'تعذر جلب Forex Factory: {last}')

def _load(provider):
    errors=[]; economic=[]; general=[]; economic_ok=False; general_ok=False
    if provider in ('finnhub','auto'):
        try:economic=_fetch_finnhub_economic(); economic_ok=True
        except Exception as e:economic_ok=False; errors.append(str(e))
        if NEWS_GENERAL_ENABLED:
            try:general=_fetch_finnhub_general(); general_ok=True
            except Exception as e:general_ok=False; errors.append(str(e))
        else:general_ok=True
        if economic_ok:return economic,general,None,economic_ok,general_ok
    try:economic=_fetch_forexfactory(); return economic,general,None,True,general_ok
    except Exception as e:
        errors.append(str(e)); return [],general,' | '.join(errors),False,general_ok

def get_news_status(symbol,settings=None):
    settings=settings or {}; enabled=settings.get('news_enabled',NEWS_ENABLED)
    if not enabled:return {'blocked':False,'reason':'فلتر الأخبار معطل','event':None,'health':'DISABLED'}
    provider=str(settings.get('news_provider',NEWS_PROVIDER)).lower(); before=timedelta(minutes=int(settings.get('news_before',NEWS_BLOCK_MINUTES_BEFORE))); after=timedelta(minutes=int(settings.get('news_after',NEWS_BLOCK_MINUTES_AFTER)))
    now_ts=datetime.now(timezone.utc).timestamp()
    with LOCK:
        if now_ts-CACHE['time']>NEWS_CACHE_SECONDS or CACHE['provider']!=provider:
            ev,gen,err,eok,gok=_load(provider); CACHE.update(time=now_ts,events=ev,general=gen,error=err,provider=provider,economic_ok=eok,general_ok=gok)
        events=list(CACHE['events']); general=list(CACHE['general']); error=CACHE['error']; eok=CACHE['economic_ok']; gok=CACHE['general_ok']
    fail_closed=bool(settings.get('news_fail_closed',NEWS_FAIL_CLOSED)); now=datetime.now(timezone.utc); currencies=SYMBOL_CURRENCIES.get(symbol.upper(),{'USD'})
    for e in events:
        if e.get('impact')=='HIGH' and e.get('currency') in currencies and e['time']-before<=now<=e['time']+after:
            return {'blocked':True,'reason':f"خبر عالي التأثير: {e['title']}",'event':e,'error':error,'health':'BLOCKED_NEWS','economic_ok':eok,'general_ok':gok}
    recent=timedelta(minutes=int(settings.get('news_recent_minutes',NEWS_RECENT_MINUTES)))
    for n in general:
        if n.get('time') and now-recent<=n['time']<=now:
            return {'blocked':False,'reason':f"خبر مؤثر حديث: {n['title'][:120]}",'event':n,'error':error,'health':'WARNING','economic_ok':eok,'general_ok':gok}
    if not eok:
        if fail_closed:return {'blocked':True,'reason':'تعذر التحقق من التقويم الاقتصادي؛ تم إيقاف الإشارة احتياطياً','event':None,'error':error,'health':'ERROR','economic_ok':False,'general_ok':gok}
        return {'blocked':False,'reason':'التقويم الاقتصادي غير متاح؛ لم يتم فرض حظر احتياطي','event':None,'error':error,'health':'DEGRADED','economic_ok':False,'general_ok':gok}
    if not gok and NEWS_GENERAL_ENABLED:
        return {'blocked':False,'reason':'التقويم الاقتصادي يعمل؛ الأخبار العامة غير متاحة','event':None,'error':error,'health':'PARTIAL','economic_ok':True,'general_ok':False}
    return {'blocked':False,'reason':'لا يوجد خبر USD عالي التأثير ضمن نافذة الحظر','event':None,'health':'OK','economic_ok':True,'general_ok':gok}
