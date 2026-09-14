def market_quality(candles, atr_value):
    if len(candles) < 40:
        return {"allowed": False, "reason": "بيانات غير كافية"}
    if not atr_value or atr_value <= 0:
        return {"allowed": False, "reason": "ATR غير صالح"}
    ranges = [c["high"] - c["low"] for c in candles[-30:]]
    avg = sum(ranges) / len(ranges)
    latest = ranges[-1]
    if avg < atr_value * 0.35:
        return {"allowed": False, "reason": "التذبذب منخفض جدًا"}
    if latest > atr_value * 4.0:
        return {"allowed": False, "reason": "شمعة اندفاعية شاذة؛ انتظار استقرار السعر"}
    return {"allowed": True, "reason": "جودة السوق مقبولة"}
