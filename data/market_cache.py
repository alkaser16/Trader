import time
import threading
from data.market import get_candles

_CACHE = {}
_LOCK = threading.Lock()


def get_cached_candles(symbol, interval, outputsize=360, ttl=45):
    key = (symbol.upper(), interval, int(outputsize))
    now = time.time()
    with _LOCK:
        item = _CACHE.get(key)
        if item and now - item[0] < ttl:
            return list(item[1])
    candles = get_candles(symbol, interval, outputsize)
    with _LOCK:
        _CACHE[key] = (now, list(candles))
    return candles


def clear_cache():
    with _LOCK:
        _CACHE.clear()
