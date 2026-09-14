# GOLD BOT V4.3

نسخة كاملة من المشروع، موجهة للعمل على Termux بدون pandas/numpy عبر pip.

## أهم ما في V4.3
- مراقبة XAU/USD تلقائياً 24/5.
- جلسة لندن/نيويورك أفضلية وليست حظراً زمنياً.
- HTF + Structure + Liquidity + FVG + Order Blocks + EMA/RSI/MACD/ADX.
- Entry / SL / TP1 / TP2 / TP3 عند تحقق الشروط.
- فلتر أخبار اقتصادي مع Finnhub ثم Forex Factory كاحتياط في وضع AUTO.
- فشل الأخبار العامة وحدها لا يمنع الصفقة.
- `NEWS_FAIL_CLOSED=false` افتراضياً حتى لا يتوقف البوت بسبب API معطل؛ يمكن تشغيله من الإعدادات للحذر.
- مختبر Telegram: Backtest + Score Lab + Walk-Forward.
- التقارير تعرض Win Rate وProfit Factor وExpectancy وMax Drawdown وسلسلة الخسائر وBUY/SELL.

## التشغيل
1. ضع المشروع داخل `~/gold`.
2. احتفظ بملف `.env` الحالي ولا تستبدله.
3. تأكد من وجود `ADMIN_CHAT_IDS`، ويمكن أيضاً أن يقرأ `ADMIN_CHAT_ID` القديم.
4. شغّل:

```bash
python -m compileall -q .
python main.py
```

## الاختبار
من Telegram:
- `🧪 مختبر الاستراتيجية`
- `📊 Backtest`
- `🎯 تحسين Score`
- `🔬 Walk-Forward`

أو:
```bash
python run_backtest.py
python walk_forward.py
python optimize_score.py
```

### تنبيه منهجي
Backtest لا يستخدم الأخبار التاريخية الكاملة، لذلك لا ينبغي اعتباره محاكاة كاملة لكل ظروف السوق. كما أن نتائج الماضي لا تضمن نتائج مستقبلية. Score هو قوة إعداد وليس احتمال نجاح.
