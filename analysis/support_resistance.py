from analysis.structure import find_swing_highs, find_swing_lows


def get_support_resistance(candles):
    highs = find_swing_highs(candles)
    lows = find_swing_lows(candles)
    supports = [x[1] for x in lows[-10:]]
    resistances = [x[1] for x in highs[-10:]]
    return {"supports": supports, "resistances": resistances}


def evaluate_sr(price, atr_value, levels):
    if not atr_value:
        return {"support": None, "resistance": None, "score": 0}
    supports = [x for x in levels["supports"] if x < price]
    resistances = [x for x in levels["resistances"] if x > price]
    support = max(supports) if supports else None
    resistance = min(resistances) if resistances else None
    score = 0
    if support is not None and price - support <= atr_value * 0.65:
        score += 8
    if resistance is not None and resistance - price <= atr_value * 0.65:
        score -= 8
    return {"support": support, "resistance": resistance, "score": score}
