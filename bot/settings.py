import json,os,threading
PATH=os.path.join(os.path.dirname(os.path.dirname(__file__)),'data','bot_settings.json'); LOCK=threading.Lock()
DEFAULTS={'monitor_enabled':True,'symbol':'XAU/USD','timeframe':'15m','min_score':75,'min_edge':12,'min_confirmations':4,'strict_mode':True,'news_enabled':True,'news_provider':'auto','news_fail_closed':False,'news_general_enabled':True,'news_before':45,'news_after':30,'news_recent_minutes':60,'session_filter_enabled':True,'session_start_utc':7,'session_end_utc':21,'session_score_penalty':0,'session_edge_penalty':0,'min_rr':1.8,'send_no_trade':False,'signal_profile':'balanced','lab_days':30,'optimizer_days':60,'optimizer_limit':80,'atr_sl_multiplier':1.25,'swing_lookback':25}
def _load():
 os.makedirs(os.path.dirname(PATH),exist_ok=True)
 try:
  with open(PATH,'r',encoding='utf-8') as f:data=json.load(f)
 except Exception:data={}
 out=DEFAULTS.copy();out.update(data);return out
def _save(data):
 os.makedirs(os.path.dirname(PATH),exist_ok=True);tmp=PATH+'.tmp'
 with open(tmp,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
 os.replace(tmp,PATH)
def get():
 with LOCK:return _load()
def update(**kwargs):
 with LOCK:data=_load();data.update(kwargs);_save(data);return data
