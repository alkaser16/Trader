# GOLD BOT V3 — Termux

نسخة V3 تضيف مراقبة تلقائية للذهب كل ~60 ثانية، مع لوحة تحكم كاملة من Telegram.

## 1) التثبيت

```bash
cd ~
unzip goldbot_v3.zip -d goldbot_v3
cd goldbot_v3/goldbot
python -m pip install -r requirements.txt
cp .env.example .env
nano .env
```

## 2) أين أضع Finnhub؟

داخل ملف `.env` فقط:

```env
FINNHUB_API_KEY=ضع_مفتاحك_هنا
NEWS_PROVIDER=finnhub
NEWS_ENABLED=true
NEWS_FAIL_CLOSED=true
```

لا تضع المفتاح داخل `news.py` أو `telegram.py`.

## 3) Telegram Admin

ضع Chat ID الخاص بك في:

```env
ADMIN_CHAT_IDS=123456789
```

إذا لم تعرفه، أرسل `/id` للبوت. سيعرض لك Chat ID لتضعه في `.env` ثم أعد تشغيل البوت.

## 4) التشغيل

```bash
python main.py
```

البوت سيشغل:
- Telegram Bot
- Auto Monitor للذهب
- فحص دوري كل 60 ثانية تقريبًا
- لا يرسل رسالة عند NO_TRADE
- يمنع تكرار نفس الإشارة

## 5) التحكم من Telegram

من `/start` أو `/menu`:

- تحليل الذهب الآن
- تشغيل/إيقاف المراقبة
- تغيير الفريم
- تغيير Minimum Score
- تغيير Minimum Edge
- تشغيل/إيقاف فلتر الأخبار
- تبديل Finnhub / Forex Factory
- تحديد دقائق الحظر قبل وبعد الخبر
- عرض حالة النظام

## ملاحظة عن الأخبار

Finnhub Economic Calendar مفيد للأحداث الاقتصادية، خصوصًا أحداث USD عالية التأثير. لا ينبغي اعتباره تغطية كاملة لكل خبر جيوسياسي أو عاجل يؤثر في الذهب؛ لذلك V3 لا يدّعي أن تقويمًا واحدًا يغطي كل مؤثرات XAU/USD.

## أمان

اعتبر أي Token/API Key سبق وضعه داخل ملفات أو مشاركته مكشوفًا، وأعد توليده قبل استخدام النسخة الجديدة.
