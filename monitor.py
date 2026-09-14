import threading,time,traceback
from analysis.strategy import analyze
from bot.settings import get
from config import ADMIN_CHAT_IDS,MONITOR_INTERVAL_SECONDS
STOP=threading.Event();LAST_SENT_ID=None

def _fmt(x):return '—' if x is None else f'{x:.3f}'
def format_signal(r):
 return f"🤖 GOLD AUTO SIGNAL V4.5\n━━━━━━━━━━━━━━━━\n\n{'🟢 BUY' if r['signal']=='BUY' else '🔴 SELL'}\n📌 {r['symbol']} | {r['timeframe']} | HTF {r['higher_timeframe']}\n⭐ Score {r['effective_score']}/100 | Edge {r['effective_edge']} | Confirm {r['confirmations']}\n\n💰 Entry: {_fmt(r['price'])}\n🛑 SL: {_fmt(r['stop_loss'])}\n🎯 TP1: {_fmt(r['tp1'])}\n🎯 TP2: {_fmt(r['tp2'])}\n🎯 TP3: {_fmt(r['tp3'])}\n📐 RR TP2: 1:{r['rr_tp2']:.2f}\n\n📈 Trend: {r['trend']}\n🏗 Structure: {r['structure']} / HTF {r['higher_structure']}\n📊 RSI {r['rsi']:.1f} | ADX {r['adx']:.1f}\n💧 Sweep {r['smc']['liquidity_sweep']} | FVG {r['smc']['fvg_bias']} | OB {r['smc']['ob_bias']}\n⚡ Displacement {r['smc']['displacement']}\n📰 {r['news']['reason']}\n🕐 {r['session']}\n\n⚠️ تحليل تعليمي؛ لا توجد نسبة نجاح مضمونة."

def run_cycle(send_message):
 global LAST_SENT_ID
 s=get()
 if not s['monitor_enabled'] or not ADMIN_CHAT_IDS:return
 r=analyze(s['symbol'],s['timeframe'],settings=s)
 if r['signal'] not in {'BUY','SELL'}:return
 sid=(r['symbol'],r['timeframe'],r.get('candle_time'),r['signal'])
 if sid==LAST_SENT_ID:return
 LAST_SENT_ID=sid
 for cid in list(ADMIN_CHAT_IDS):
  try:send_message(cid,format_signal(r))
  except Exception:traceback.print_exc()

def worker(send_message):
 print('GOLD V4.5 auto-monitor started')
 while not STOP.is_set():
  t=time.time()
  try:run_cycle(send_message)
  except Exception as e:print('Monitor error:',e);traceback.print_exc()
  STOP.wait(max(5,MONITOR_INTERVAL_SECONDS-(time.time()-t)))
def start(send_message):
 t=threading.Thread(target=worker,args=(send_message,),daemon=True,name='gold-monitor');t.start();return t
