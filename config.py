import os
from dotenv import load_dotenv
load_dotenv()
def _bool(n,d=True):return os.getenv(n,str(d)).strip().lower() in {'1','true','yes','on'}
def _int(n,d):
 try:return int(os.getenv(n,str(d)))
 except:return d
def _float(n,d):
 try:return float(os.getenv(n,str(d)))
 except:return d
TWELVE_DATA_API_KEY=os.getenv('TWELVE_DATA_API_KEY','').strip();TELEGRAM_BOT_TOKEN=os.getenv('TELEGRAM_BOT_TOKEN','').strip();FINNHUB_API_KEY=os.getenv('FINNHUB_API_KEY','').strip();SYMBOL=os.getenv('SYMBOL','XAU/USD').strip().upper()
MIN_SCORE=_int('MIN_SCORE',75);MIN_EDGE=_int('MIN_EDGE',12);STRICT_MODE=_bool('STRICT_MODE',True);MIN_CONFIRMATIONS=_int('MIN_CONFIRMATIONS',4)
NEWS_ENABLED=_bool('NEWS_ENABLED',True);NEWS_FAIL_CLOSED=_bool('NEWS_FAIL_CLOSED',False);NEWS_BLOCK_MINUTES_BEFORE=_int('NEWS_BLOCK_MINUTES_BEFORE',45);NEWS_BLOCK_MINUTES_AFTER=_int('NEWS_BLOCK_MINUTES_AFTER',30);NEWS_CACHE_SECONDS=_int('NEWS_CACHE_SECONDS',180);NEWS_PROVIDER=os.getenv('NEWS_PROVIDER','auto').strip().lower();NEWS_GENERAL_ENABLED=_bool('NEWS_GENERAL_ENABLED',True);NEWS_RECENT_MINUTES=_int('NEWS_RECENT_MINUTES',60)
SESSION_FILTER_ENABLED=_bool('SESSION_FILTER_ENABLED',True);SESSION_START_UTC=_int('SESSION_START_UTC',7);SESSION_END_UTC=_int('SESSION_END_UTC',21);SESSION_SCORE_PENALTY=_int('SESSION_SCORE_PENALTY',0);SESSION_EDGE_PENALTY=_int('SESSION_EDGE_PENALTY',0);SESSION_SCORE_BONUS=_int('SESSION_SCORE_BONUS',3);SESSION_EDGE_BONUS=_int('SESSION_EDGE_BONUS',2)
ATR_SL_MULTIPLIER=_float('ATR_SL_MULTIPLIER',1.25);SWING_LOOKBACK=_int('SWING_LOOKBACK',25);MIN_RR=_float('MIN_RR',1.8);ATR_SL_MULTIPLIER=_float('ATR_SL_MULTIPLIER',1.25);SWING_LOOKBACK=_int('SWING_LOOKBACK',25);POLL_TIMEOUT=_int('POLL_TIMEOUT',30);REQUEST_TIMEOUT=_int('REQUEST_TIMEOUT',30);ANALYSIS_COOLDOWN_SECONDS=_int('ANALYSIS_COOLDOWN_SECONDS',20);MONITOR_INTERVAL_SECONDS=_int('MONITOR_INTERVAL_SECONDS',60)
ADMIN_CHAT_IDS=set()
_admin_raw=os.getenv('ADMIN_CHAT_IDS', os.getenv('ADMIN_CHAT_ID',''))
for x in _admin_raw.split(','):
 try:
  if x.strip():ADMIN_CHAT_IDS.add(int(x.strip()))
 except:pass
if not TWELVE_DATA_API_KEY:raise RuntimeError('TWELVE_DATA_API_KEY is missing in .env')
if not TELEGRAM_BOT_TOKEN:raise RuntimeError('TELEGRAM_BOT_TOKEN is missing in .env')
