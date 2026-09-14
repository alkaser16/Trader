import time,threading,requests,traceback
from config import TELEGRAM_BOT_TOKEN,POLL_TIMEOUT,REQUEST_TIMEOUT,ANALYSIS_COOLDOWN_SECONDS,ADMIN_CHAT_IDS
from analysis.strategy import analyze
from analysis.news import get_news_status
from bot.settings import get,update
from backtest.lab import run_backtest,optimize_scores,walk_forward
from backtest.optimizer import optimize,out_of_sample,walk_forward_auto,load_best
BASE_URL='https://api.telegram.org/bot'+TELEGRAM_BOT_TOKEN
user_states={};last_analysis={}

def telegram_request(method,payload=None):
 r=requests.post(BASE_URL+'/'+method,json=payload or {},timeout=REQUEST_TIMEOUT);r.raise_for_status();d=r.json()
 if not d.get('ok'):raise RuntimeError(d.get('description','Telegram API error'))
 return d

def send_message(chat_id,text,keyboard=None):
 p={'chat_id':chat_id,'text':text,'disable_web_page_preview':True}
 if keyboard:p['reply_markup']={'inline_keyboard':keyboard}
 telegram_request('sendMessage',p)

def answer_callback(cid):
 try:telegram_request('answerCallbackQuery',{'callback_query_id':cid})
 except Exception:pass

def is_admin(cid):return cid in ADMIN_CHAT_IDS

def menu():
 s=get();mon='🟢' if s['monitor_enabled'] else '🔴';news='🟢' if s['news_enabled'] else '🔴';p=s.get('signal_profile','balanced').upper()
 return [[{'text':'🥇 تحليل الآن','callback_data':'analyze'},{'text':f'📡 المراقبة {mon}','callback_data':'monitor'}],[{'text':f'🎯 {p}','callback_data':'profile'},{'text':f'📰 الأخبار {news}','callback_data':'news'}],[{'text':'🧪 مختبر الاستراتيجية','callback_data':'lab'},{'text':'🏆 المُحسِّن الآلي','callback_data':'optimizer'}],[{'text':'📊 الحالة','callback_data':'status'},{'text':'⚙️ الإعدادات','callback_data':'settings'}],[{'text':'ℹ️ المساعدة','callback_data':'help'}]]

def settings_menu():
 s=get();return [[{'text':f"📡 المراقبة {'🟢' if s['monitor_enabled'] else '🔴'}",'callback_data':'toggle_monitor'},{'text':f"📰 الأخبار {'🟢' if s['news_enabled'] else '🔴'}",'callback_data':'toggle_news'}],[{'text':f"⏱ الفريم {s['timeframe']}",'callback_data':'set_tf'},{'text':f"🎯 {s.get('signal_profile','balanced').upper()}",'callback_data':'profile'}],[{'text':f"⭐ Score ≥ {s['min_score']}",'callback_data':'set_score'},{'text':f"📐 Edge ≥ {s['min_edge']}",'callback_data':'set_edge'}],[{'text':f"🧩 Confirm ≥ {s['min_confirmations']}",'callback_data':'set_confirm'},{'text':f"📊 RR ≥ {s['min_rr']}",'callback_data':'set_rr'}],[{'text':f"🧠 Strict {'🟢' if s['strict_mode'] else '🔴'}",'callback_data':'toggle_strict'},{'text':f"🕐 أفضلية الجلسة {'🟢' if s['session_filter_enabled'] else '🔴'}",'callback_data':'toggle_session'}],[{'text':f"🛡 Fail-closed {'🟢' if s['news_fail_closed'] else '🔴'}",'callback_data':'toggle_failclosed'},{'text':f"🗞 المصدر {s['news_provider']}",'callback_data':'provider'}],[{'text':f"⏮ قبل الخبر {s['news_before']}m",'callback_data':'set_before'},{'text':f"⏭ بعد الخبر {s['news_after']}m",'callback_data':'set_after'}],[{'text':'🏆 المُحسِّن الآلي','callback_data':'optimizer'},{'text':'⬅️ الرئيسية','callback_data':'home'}]]

def profile_menu():return [[{'text':'🛡 محافظ | 85 / 18 / 4','callback_data':'profile:conservative'}],[{'text':'⚖️ متوازن | 75 / 12 / 4','callback_data':'profile:balanced'}],[{'text':'📡 نشط | 70 / 10 / 3','callback_data':'profile:active'}],[{'text':'⬅️ الإعدادات','callback_data':'settings'}]]

def timeframe_menu():return [[{'text':'5m','callback_data':'tf:5m'},{'text':'15m','callback_data':'tf:15m'},{'text':'30m','callback_data':'tf:30m'}],[{'text':'1h','callback_data':'tf:1h'},{'text':'4h','callback_data':'tf:4h'}],[{'text':'⬅️ الإعدادات','callback_data':'settings'}]]

def lab_menu():
 return [[{'text':'📊 Backtest','callback_data':'lab:backtest'},{'text':'🎯 Score Lab','callback_data':'lab:opt'}],[{'text':'🔬 Walk-Forward','callback_data':'lab:wf'},{'text':'🧪 Out-of-Sample','callback_data':'lab:oos'}],[{'text':'🏆 Auto Optimizer','callback_data':'optimizer'},{'text':'⬅️ الرئيسية','callback_data':'home'}]]

def optimizer_menu():
 return [[{'text':'🚀 تشغيل Auto Optimizer','callback_data':'opt:run'}],[{'text':'🔬 Out-of-Sample','callback_data':'lab:oos'},{'text':'🪟 Walk-Forward Auto','callback_data':'opt:wf'}],[{'text':'📋 أفضل إعداد محفوظ','callback_data':'opt:show'},{'text':'💾 تطبيق الأفضل','callback_data':'opt:apply'}],[{'text':'⬅️ الرئيسية','callback_data':'home'}]]

def fmt(x):return '—' if x is None else f'{x:.3f}'

def format_result(r):
 h=f"🤖 GOLD BOT V4.5\n━━━━━━━━━━━━━━━━\n📌 {r['symbol']} • {r['timeframe']} • HTF {r['higher_timeframe']}";m=f"⭐ Score {r['effective_score']}/100  |  📐 Edge {r['effective_edge']}  |  🧩 {r['confirmations']} تأكيد";c=f"📈 {r['trend']} | 🏗 {r['structure']} | 📊 RSI {r['rsi']:.1f} | ADX {r['adx']:.1f}"
 if r['signal']=='NO_TRADE':
  rs='\n'.join('• '+x for x in r.get('reasons',[])[:6]) or '• لا يوجد سبب مسجل'
  return f"{h}\n\n⚪ NO TRADE\n{m}\n{c}\n\n📰 {r['news']['reason']}\n🕐 {r['session']}\n\n🔎 سبب الرفض\n{rs}\n\n💡 Score قوة الإعداد وليس نسبة نجاح مضمونة."
 icon='🟢 BUY' if r['signal']=='BUY' else '🔴 SELL';rs='\n'.join('• '+x for x in r.get('reasons',[])[:7])
 return f"{h}\n\n{icon}\n{m}\n{c}\n\n💰 Entry  {fmt(r['price'])}\n🛑 SL     {fmt(r['stop_loss'])}\n🎯 TP1    {fmt(r['tp1'])}\n🎯 TP2    {fmt(r['tp2'])}\n🎯 TP3    {fmt(r['tp3'])}\n📊 RR TP2  1:{r['rr_tp2']:.2f}\n\n💧 Sweep {r['smc']['liquidity_sweep']} | FVG {r['smc']['fvg_bias']} | OB {r['smc']['ob_bias']}\n⚡ Displacement {r['smc']['displacement']}\n📰 {r['news']['reason']}\n🕐 {r['session']}\n\n🧠 عوامل الاتجاه:\n{rs}\n\n⚠️ إشارة تحليلية وليست ضماناً للنتيجة."

def run_analysis_async(cid):
 now=time.time()
 if now-last_analysis.get(cid,0)<ANALYSIS_COOLDOWN_SECONDS:return send_message(cid,'⏳ انتظر قليلاً قبل إعادة التحليل.')
 last_analysis[cid]=now;s=get();send_message(cid,f"⏳ جارٍ تحليل XAU/USD على {s['timeframe']}...\nHTF + Structure + Liquidity + FVG + OB + EMA/RSI/MACD/ADX + News")
 try:send_message(cid,format_result(analyze(s['symbol'],s['timeframe'],s)),[[{'text':'🔄 إعادة','callback_data':'analyze'},{'text':'⚙️ الإعدادات','callback_data':'settings'}],[{'text':'🧪 المختبر','callback_data':'lab'}]])
 except Exception as e:send_message(cid,'❌ فشل التحليل:\n'+str(e)[:1000])

def lab_backtest_async(cid):
 s=get();send_message(cid,f"🧪 بدء Backtest\n📌 {s['symbol']} • {s['timeframe']}\n📅 آخر 30 يوم\n\nقد يستغرق التحميل وقتاً حسب API...")
 try:
  m,_=run_backtest(s['symbol'],s['timeframe'],30,s['min_score'],s['min_edge'],s['min_confirmations'],s['strict_mode'],s['min_rr'])
  pf='∞' if m['profit_factor']==float('inf') else f"{m['profit_factor']:.2f}"
  text=f"🧪 GOLD BOT V4.5 — BACKTEST\n━━━━━━━━━━━━━━━━\n📌 {s['symbol']} • {s['timeframe']}\n📅 آخر 30 يوم\n🕯 البيانات: {m['candles']} شمعة\n\n📊 الصفقات: {m['total']}\n🟢 رابحة: {m['wins']}\n🔴 خاسرة: {m['losses']}\n🎯 Win Rate: {m['win_rate']:.2f}%\n\n💰 Profit Factor: {pf}\n📈 Net: {m['net_r']:.2f}R\n📐 Expectancy: {m['expectancy_r']:.3f}R\n📉 Max DD: {m['max_drawdown_r']:.2f}R\n🔥 أطول خسائر متتالية: {m['max_loss_streak']}\n\n🟢 BUY: {m['buy_total']} | {m['buy_win_rate']:.1f}%\n🔴 SELL: {m['sell_total']} | {m['sell_win_rate']:.1f}%\n\n⚠️ اختبار تاريخي تقني؛ الأخبار التاريخية ليست مدخلاً كاملاً في هذا الاختبار. النتائج لا تضمن المستقبل."
  send_message(cid,text,lab_menu())
 except Exception as e:send_message(cid,'❌ فشل Backtest:\n'+str(e)[:1200],lab_menu())

def lab_opt_async(cid):
 s=get();send_message(cid,f"🎯 اختبار مستويات Score\n📌 {s['symbol']} • {s['timeframe']}\n📅 آخر 30 يوم\n\nيتم اختبار 60/65/70/75/80/85/90...")
 try:
  rows,best,n=optimize_scores(s['symbol'],s['timeframe'],30,min_edge=s['min_edge'],min_confirm=s['min_confirmations'],strict=s['strict_mode'],min_rr=s['min_rr']);lines=['🎯 SCORE LAB V4.5','━━━━━━━━━━━━━━━━',f"📌 {s['symbol']} • {s['timeframe']}",'','Score | Trades | Win% | PF | ExpR | DD']
  for r in rows:lines.append(f"{r['score']:>5} | {r['total']:>6} | {r['win_rate']:>5.1f}% | {r['profit_factor']:>4.2f} | {r['expectancy_r']:>+.3f} | {r['max_drawdown_r']:>4.1f}")
  lines += ['', f"🏆 أفضل مستوى تاريخياً: {best['score'] if best else 'لا توجد نتائج كافية'}", '', '⚠️ الأفضل تاريخياً ليس ضماناً للمستقبل. لا تعتمد على Win Rate وحده.']
  send_message(cid,'\n'.join(lines),lab_menu())
 except Exception as e:send_message(cid,'❌ فشل تحسين Score:\n'+str(e)[:1200],lab_menu())

def lab_wf_async(cid):
 s=get();send_message(cid,f"🔬 Walk-Forward\n📌 {s['symbol']} • {s['timeframe']}\n📅 90 يوم | تدريب 30 | اختبار 10\n\nيتم اختيار Score على بيانات التدريب ثم اختباره على بيانات لم تُستخدم في الاختيار...")
 try:
  r=walk_forward(s['symbol'],s['timeframe'],90,30,10,min_edge=s['min_edge'],min_confirm=s['min_confirmations'],strict=s['strict_mode'],min_rr=s['min_rr']);text=f"🔬 WALK-FORWARD V4.5\n━━━━━━━━━━━━━━━━\n📌 {s['symbol']} • {s['timeframe']}\n🪟 النوافذ: {r['windows']}\n🟢 نوافذ Expectancy موجبة: {r['positive_windows']}/{r['windows']} ({r['positive_pct']:.1f}%)\n\n"
  for i,x in enumerate(r['results'],1):text+=f"Window {i}: Score {x['score']} | {x['total']} trades | Win {x['win_rate']:.1f}% | PF {x['profit_factor']:.2f} | {x['net_r']:+.2f}R\n"
  text+='\n⚠️ هذا اختبار خارج العينة نسبياً، وليس ضماناً للأداء المستقبلي.';send_message(cid,text,lab_menu())
 except Exception as e:send_message(cid,'❌ فشل Walk-Forward:\n'+str(e)[:1200],lab_menu())

def _fmt_best(b):
 p=b['params'];pf='∞' if b['profit_factor']==float('inf') else f"{b['profit_factor']:.2f}"
 return (f"🏆 أفضل إعداد V4.5\n━━━━━━━━━━━━━━━━\n⭐ Score ≥ {p['min_score']} | Edge ≥ {p['min_edge']} | Confirm ≥ {p['min_confirmations']}\n🧠 Strict: {'ON' if p['strict_mode'] else 'OFF'} | RR ≥ {p['min_rr']}\n🛑 ATR SL: {p['atr_sl_multiplier']} | Swing: {p['swing_lookback']}\n\n📊 Trades: {b['total']}\n🎯 Win Rate: {b['win_rate']:.1f}%\n💰 Profit Factor: {pf}\n📈 Net: {b['net_r']:+.2f}R\n📐 Expectancy: {b['expectancy_r']:+.3f}R\n📉 Max DD: {b['max_drawdown_r']:.2f}R\n🔥 Max loss streak: {b['max_loss_streak']}\n\n⚠️ هذا أفضل إعداد وفق دالة تقييم مقاومة للإفراط في الملاءمة، وليس ضماناً للمستقبل.")

def optimizer_async(cid):
 s=get();days=int(s.get('optimizer_days',60));limit=int(s.get('optimizer_limit',160));send_message(cid,f"🚀 بدء Auto Optimizer V4.5\n📌 {s['symbol']} • {s['timeframe']}\n📅 تدريب: {days} يوم\n🔢 تركيبات: حتى {limit}\n\nسيختبر Score + Edge + Confirm + Strict + RR + ATR SL + Swing Lookback، ثم يحفظ أفضل إعداد.",optimizer_menu())
 try:
  r=optimize(s['symbol'],s['timeframe'],days,limit); b=r.get('best')
  if not b: return send_message(cid,'❌ لم توجد تركيبات كافية. زد الفترة أو خفّض الشروط مؤقتاً.',optimizer_menu())
  send_message(cid,_fmt_best(b)+f"\n\n🔢 تم اختبار {r['tested']} تركيبة.",optimizer_menu())
 except Exception as e:send_message(cid,'❌ فشل Auto Optimizer:\n'+str(e)[:1400],optimizer_menu())

def oos_async(cid):
 s=get();send_message(cid,'🔬 بدء Out-of-Sample\n80% تدريب / 20% اختبار لم تُستخدم في اختيار الإعداد...')
 try:
  r=out_of_sample(s['symbol'],s['timeframe'],90,.8,120)
  if not r.get('ok'):return send_message(cid,'❌ '+r.get('reason','اختبار OOS غير كافٍ.'),optimizer_menu())
  p=r['params'];tm=r['train'];xm=r['test'];send_message(cid,f"🔬 OUT-OF-SAMPLE V4.5\n━━━━━━━━━━━━━━━━\n📌 {r['symbol']} • {r['timeframe']}\n\n🏋️ TRAIN\nTrades {tm['total']} | Win {tm['win_rate']:.1f}% | PF {tm['profit_factor']:.2f} | Exp {tm['expectancy_r']:+.3f}R\n\n🧪 TEST / OOS\nTrades {xm['total']} | Win {xm['win_rate']:.1f}% | PF {xm['profit_factor']:.2f} | Exp {xm['expectancy_r']:+.3f}R | DD {xm['max_drawdown_r']:.2f}R\n\n⚙️ Score {p['min_score']} | Edge {p['min_edge']} | Confirm {p['min_confirmations']} | RR {p['min_rr']} | ATR {p['atr_sl_multiplier']} | Swing {p['swing_lookback']}\n\n⚠️ إذا انهارت النتائج في OOS فهذا تحذير من الإفراط في الملاءمة.",optimizer_menu())
 except Exception as e:send_message(cid,'❌ فشل OOS:\n'+str(e)[:1400],optimizer_menu())

def wf_auto_async(cid):
 s=get();send_message(cid,'🪟 بدء Walk-Forward Auto\nكل نافذة تختار إعدادها من التدريب ثم تختبره على بيانات لاحقة...')
 try:
  r=walk_forward_auto(s['symbol'],s['timeframe'],120,30,10,80);lines=[f"🪟 WALK-FORWARD AUTO V4.5\n━━━━━━━━━━━━━━━━\nالنوافذ: {r['windows']}\nالموجبة: {r['positive_windows']}/{r['windows']} ({r['positive_pct']:.1f}%)\n"]
  for i,x in enumerate(r['results'],1):
   p=x['best_params'];m=x['test'];lines.append(f"W{i}: S{p['min_score']} E{p['min_edge']} C{p['min_confirmations']} RR{p['min_rr']} | {m['total']} trades | Win {m['win_rate']:.1f}% | PF {m['profit_factor']:.2f} | {m['expectancy_r']:+.2f}R")
  lines.append('\n⚠️ الاختبار خارج العينة داخل كل نافذة؛ لا يضمن الأداء المستقبلي.')
  send_message(cid,'\n'.join(lines),optimizer_menu())
 except Exception as e:send_message(cid,'❌ فشل Walk-Forward Auto:\n'+str(e)[:1400],optimizer_menu())

def apply_best(cid):
 r=load_best();b=r.get('best') if r else None
 if not b:return send_message(cid,'❌ لا يوجد إعداد محفوظ. شغّل Auto Optimizer أولاً.',optimizer_menu())
 p=b['params'];update(min_score=p['min_score'],min_edge=p['min_edge'],min_confirmations=p['min_confirmations'],strict_mode=p['strict_mode'],min_rr=p['min_rr'],signal_profile='optimized',atr_sl_multiplier=p['atr_sl_multiplier'],swing_lookback=p['swing_lookback']);send_message(cid,'💾 تم تطبيق أفضل إعداد محفوظ على المراقبة الحالية.\n\n'+_fmt_best(b),settings_menu())

def process_callback(cb):
 answer_callback(cb.get('id',''));msg=cb.get('message') or {};cid=msg.get('chat',{}).get('id');data=cb.get('data','')
 if not cid or not is_admin(cid):return
 if data=='home':user_states.pop(cid,None);send_message(cid,'🤖 GOLD BOT V4.5\nاختر من القائمة:',menu());return
 if data=='analyze':threading.Thread(target=run_analysis_async,args=(cid,),daemon=True).start();return
 if data=='optimizer':send_message(cid,'🏆 Auto Optimizer V4.5\n━━━━━━━━━━━━━━━━\nيبحث تلقائياً عن تركيبة متوازنة، ثم يمكنك اختبارها OOS/WF قبل تطبيقها.',optimizer_menu());return
 if data=='opt:run':threading.Thread(target=optimizer_async,args=(cid,),daemon=True).start();return
 if data=='opt:apply':apply_best(cid);return
 if data=='opt:show':
  r=load_best(); b=r.get('best') if r else None; send_message(cid,_fmt_best(b) if b else '❌ لا يوجد إعداد محفوظ.',optimizer_menu());return
 if data=='opt:wf':threading.Thread(target=wf_auto_async,args=(cid,),daemon=True).start();return
 if data=='lab':send_message(cid,'🧪 مختبر الاستراتيجية\n━━━━━━━━━━━━━━━━\nيستخدم بيانات تاريخية ويحسب Win Rate وProfit Factor وExpectancy وDrawdown.\n\n⚠️ الأخبار التاريخية ليست مدمجة بالكامل في Backtest، لذلك لا ندّعي أن الاختبار يحاكي كل خبر تاريخي.',lab_menu());return
 if data=='lab:backtest':threading.Thread(target=lab_backtest_async,args=(cid,),daemon=True).start();return
 if data=='lab:opt':threading.Thread(target=lab_opt_async,args=(cid,),daemon=True).start();return
 if data=='lab:wf':threading.Thread(target=lab_wf_async,args=(cid,),daemon=True).start();return
 if data=='lab:oos':threading.Thread(target=oos_async,args=(cid,),daemon=True).start();return
 if data=='monitor':
  s=get();send_message(cid,f"📡 المراقبة {'🟢 تعمل' if s['monitor_enabled'] else '🔴 متوقفة'}\n\n📌 {s['symbol']} • {s['timeframe']}\n⏱ فحص كل {60}s\n🕐 مراقبة 24/5\n🎯 {s['signal_profile'].upper()} | Score {s['min_score']} | Edge {s['min_edge']} | Confirm {s['min_confirmations']}\n📰 الأخبار: {'ON' if s['news_enabled'] else 'OFF'}",settings_menu());return
 if data=='settings':send_message(cid,'⚙️ إعدادات GOLD BOT V4.5\n━━━━━━━━━━━━━━━━\nاختر ما تريد تغييره:',settings_menu());return
 if data=='toggle_monitor':update(monitor_enabled=not get()['monitor_enabled']);send_message(cid,'✅ تم تحديث المراقبة.',settings_menu());return
 if data=='toggle_news':update(news_enabled=not get()['news_enabled']);send_message(cid,'✅ تم تحديث فلتر الأخبار.',settings_menu());return
 if data=='toggle_strict':update(strict_mode=not get()['strict_mode']);send_message(cid,'✅ تم تحديث Strict.',settings_menu());return
 if data=='toggle_session':update(session_filter_enabled=not get()['session_filter_enabled']);send_message(cid,'✅ الجلسة الآن أفضلية فقط؛ لا يوجد حظر زمني.',settings_menu());return
 if data=='toggle_failclosed':update(news_fail_closed=not get()['news_fail_closed']);send_message(cid,'✅ تم تحديث Fail-closed للأخبار.',settings_menu());return
 if data=='provider':
  p=get()['news_provider'];update(news_provider='auto' if p!='auto' else 'finnhub');send_message(cid,'🗞 المصدر: AUTO يحاول Finnhub ثم Forex Factory عند الحاجة.',settings_menu());return
 if data=='profile':send_message(cid,'🎯 اختر نمط الإشارات:',profile_menu());return
 if data.startswith('profile:'):
  p=data.split(':',1)[1];pres={'conservative':{'min_score':85,'min_edge':18,'min_confirmations':4,'strict_mode':True,'min_rr':2.0},'balanced':{'min_score':75,'min_edge':12,'min_confirmations':4,'strict_mode':True,'min_rr':1.8},'active':{'min_score':70,'min_edge':10,'min_confirmations':3,'strict_mode':False,'min_rr':1.6}}[p];update(signal_profile=p,**pres);send_message(cid,f'✅ تم اختيار {p.upper()}.',settings_menu());return
 if data=='reset_profile':update(signal_profile='balanced',min_score=75,min_edge=12,min_confirmations=4,strict_mode=True,min_rr=1.8);send_message(cid,'♻️ تمت استعادة Balanced.',settings_menu());return
 if data=='set_tf':send_message(cid,'⏱ اختر فريم المراقبة والاختبار:',timeframe_menu());return
 if data.startswith('tf:'):update(timeframe=data.split(':',1)[1]);send_message(cid,'✅ تم تغيير الفريم.',settings_menu());return
 if data in {'set_score','set_edge','set_confirm','set_rr','set_before','set_after'}:
  user_states[cid]=data;labels={'set_score':'Score بين 60 و100','set_edge':'Edge بين 0 و60','set_confirm':'Confirm بين 3 و10','set_rr':'RR بين 1.0 و5.0','set_before':'دقائق قبل الخبر','set_after':'دقائق بعد الخبر'};send_message(cid,'✍️ '+labels[data]);return
 if data=='news':
  s=get()
  try:n=get_news_status(s['symbol'],s);health=n.get('health','?');send_message(cid,f"📰 NEWS CENTER V4.5\n━━━━━━━━━━━━━━━━\nالحالة: {health}\nالمصدر: {s['news_provider']}\nقبل الخبر: {s['news_before']}m\nبعد الخبر: {s['news_after']}m\nFail-closed: {'ON' if s['news_fail_closed'] else 'OFF'}\n\n🔎 {n['reason']}\n\nملاحظة: إذا رفض Finnhub المفتاح، يحاول AUTO استخدام Forex Factory للتقويم.",settings_menu())
  except Exception as e:send_message(cid,'❌ فحص الأخبار فشل:\n'+str(e)[:900],settings_menu())
  return
 if data=='status':
  s=get();send_message(cid,f"📊 GOLD BOT V4.5\n━━━━━━━━━━━━━━━━\n📡 المراقبة: {'🟢' if s['monitor_enabled'] else '🔴'}\n📌 {s['symbol']} • {s['timeframe']}\n🎯 {s['signal_profile'].upper()}\n⭐ Score ≥ {s['min_score']} | Edge ≥ {s['min_edge']} | Confirm ≥ {s['min_confirmations']}\n📊 RR ≥ {s['min_rr']}\n🧠 Strict: {'ON' if s['strict_mode'] else 'OFF'}\n📰 News: {'ON' if s['news_enabled'] else 'OFF'} | {s['news_provider']}\n🛡 Fail-closed: {'ON' if s['news_fail_closed'] else 'OFF'}\n🕐 24/5 + لندن/نيويورك أفضلية فقط\n🧪 المختبر: Backtest + Score Lab + Walk-Forward",menu());return
 if data=='help':send_message(cid,'ℹ️ GOLD BOT V4.5\n━━━━━━━━━━━━━━━━\n🥇 تحليل الآن: تحليل XAU/USD الحالي.\n📡 المراقبة: إشارات تلقائية عند تحقق الشروط.\n📰 الأخبار: فلتر اقتصادي مع احتياط.\n🧪 المختبر: قياس تاريخي للاستراتيجية.\n\nScore لا يساوي احتمال نجاح. الاختبار التاريخي لا يضمن المستقبل.',menu());return

def process_message(msg):
 cid=msg.get('chat',{}).get('id');text=(msg.get('text') or '').strip()
 if not cid:return
 if text=='/id' and not is_admin(cid):return send_message(cid,f'Chat ID: {cid}\nأضف هذا الرقم إلى ADMIN_CHAT_IDS في .env ثم أعد التشغيل.')
 if not is_admin(cid):return
 state=user_states.get(cid)
 if text.startswith('/start') or text.startswith('/menu'):user_states.pop(cid,None);return send_message(cid,'🤖 GOLD BOT V4.5\nاختر من القائمة:',menu())
 if text.startswith('/version'):return send_message(cid,'🤖 GOLD BOT V4.5\n🟢 الإصدار الكامل مع Strategy Lab.',menu())
 if text.startswith('/test'):return threading.Thread(target=lab_backtest_async,args=(cid,),daemon=True).start()
 if text.startswith('/opt'):return threading.Thread(target=optimizer_async,args=(cid,),daemon=True).start()
 if text.startswith('/help'):return send_message(cid,'استخدم /menu أو /test لبدء Backtest. /opt لتشغيل المحسن الآلي..',menu())
 if state:
  try:value=float(text) if state=='set_rr' else int(text)
  except:return send_message(cid,'❌ أرسل رقماً صالحاً.')
  lim={'set_score':(60,100),'set_edge':(0,60),'set_confirm':(3,10),'set_rr':(1.0,5.0),'set_before':(0,240),'set_after':(0,240)}[state];lo,hi=lim
  if not lo<=value<=hi:return send_message(cid,f'❌ القيمة بين {lo} و{hi}.')
  key={'set_score':'min_score','set_edge':'min_edge','set_confirm':'min_confirmations','set_rr':'min_rr','set_before':'news_before','set_after':'news_after'}[state];update(**{key:value});user_states.pop(cid,None);return send_message(cid,'✅ تم الحفظ.',settings_menu())
 send_message(cid,'استخدم /menu.',menu())

def process_update(u):
 if 'callback_query' in u:process_callback(u['callback_query'])
 elif u.get('message'):process_message(u['message'])

def run_bot():
 offset=None;print('GOLD V4.5 Telegram bot started')
 while True:
  try:
   p={'timeout':POLL_TIMEOUT,'limit':50,'allowed_updates':['message','callback_query']}
   if offset is not None:p['offset']=offset
   r=requests.get(BASE_URL+'/getUpdates',params=p,timeout=POLL_TIMEOUT+10);r.raise_for_status();d=r.json()
   if not d.get('ok'):raise RuntimeError(d.get('description','Telegram error'))
   for u in d.get('result',[]):
    offset=u['update_id']+1
    try:process_update(u)
    except Exception as e:print('Update error:',e)
  except Exception as e:print('Bot loop error:',e);time.sleep(5)
