import time
from datetime import datetime, timedelta

import requests

from config import TWELVE_DATA_API_KEY


BASE_URL = "https://api.twelvedata.com/time_series"

# الحد الآمن للطلب الواحد.
MAX_PER_REQUEST = 5000

# لا نريد ضرب API بسرعة كبيرة.
REQUEST_DELAY = 2.0

# عدد محاولات إعادة الطلب عند 429 أو مشاكل الشبكة.
MAX_RETRIES = 5


# ============================================================
# TIMEFRAME -> APPROXIMATE TIME DELTA
# ============================================================

TIMEFRAME_MINUTES = {
    "1min": 1,
    "5min": 5,
    "15min": 15,
    "30min": 30,
    "45min": 45,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "5h": 300,
    "8h": 480,
    "1day": 1440,
}


# ============================================================
# FETCH ONE REQUEST
# ============================================================

def _request(
    symbol,
    interval,
    start_date=None,
    end_date=None,
    outputsize=5000,
):
    params = {
        "symbol": symbol,
        "interval": interval,
        "apikey": TWELVE_DATA_API_KEY,
        "timezone": "UTC",
        "outputsize": min(
            int(outputsize),
            MAX_PER_REQUEST
        ),
    }

    if start_date is not None:
        params["start_date"] = start_date

    if end_date is not None:
        params["end_date"] = end_date

    last_error = None

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                BASE_URL,
                params=params,
                timeout=30,
            )

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if response.status_code == 429:

                wait_seconds = (
                    10 * (attempt + 1)
                )

                print(
                    f"Rate limit reached. "
                    f"Waiting {wait_seconds}s..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            response.raise_for_status()

            data = response.json()

            # Twelve Data can return errors
            # using HTTP 200.

            if data.get("status") == "error":

                message = data.get(
                    "message",
                    "Unknown Twelve Data error"
                )

                raise RuntimeError(
                    message
                )

            values = data.get(
                "values"
            )

            if not values:

                return []

            return values

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        ) as error:

            last_error = error

            wait_seconds = (
                5 * (attempt + 1)
            )

            print(
                f"Network/API error: "
                f"{error}"
            )

            print(
                f"Retrying in "
                f"{wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

        except Exception as error:

            last_error = error

            break

    raise RuntimeError(
        f"Unable to fetch market data: "
        f"{last_error}"
    )


# ============================================================
# PARSE CANDLES
# ============================================================

def _parse_values(values):

    candles = []

    for item in values:

        try:

            candles.append({
                "datetime": item["datetime"],

                "open": float(
                    item["open"]
                ),

                "high": float(
                    item["high"]
                ),

                "low": float(
                    item["low"]
                ),

                "close": float(
                    item["close"]
                ),
            })

        except (
            KeyError,
            ValueError,
            TypeError,
        ):

            continue

    return candles


# ============================================================
# FETCH RECENT DATA
# ============================================================

def get_candles(
    symbol="XAU/USD",
    interval="5min",
    outputsize=300,
):
    """
    Fetch the most recent candles.

    Twelve Data allows up to 5000 records
    in a single request.
    """

    outputsize = min(
        int(outputsize),
        MAX_PER_REQUEST
    )

    values = _request(
        symbol=symbol,
        interval=interval,
        outputsize=outputsize,
    )

    candles = _parse_values(
        values
    )

    candles.sort(
        key=lambda x: x["datetime"]
    )

    return candles


# ============================================================
# FETCH HISTORICAL DATA
# ============================================================

def get_historical_candles(
    symbol="XAU/USD",
    interval="1day",
    total_candles=10000,
):
    """
    Download historical candles in multiple
    requests.

    We never request more than 5000 points
    in one API request.

    The function walks backwards in time
    and combines all returned data.
    """

    total_candles = int(
        total_candles
    )

    if total_candles <= 0:

        raise ValueError(
            "total_candles must be > 0"
        )

    if interval not in TIMEFRAME_MINUTES:

        raise ValueError(
            f"Unsupported interval: "
            f"{interval}"
        )

    minutes = TIMEFRAME_MINUTES[
        interval
    ]

    all_candles = {}

    remaining = total_candles

    end_datetime = datetime.utcnow()

    request_number = 1

    while remaining > 0:

        request_size = min(
            remaining,
            MAX_PER_REQUEST
        )

        print(
            f"Historical request "
            f"#{request_number}: "
            f"{symbol} {interval} "
            f"size={request_size}"
        )

        # ----------------------------------------------------
        # Calculate an approximate date range.
        #
        # We intentionally request a little more time
        # than strictly necessary because markets can have
        # missing periods/weekends.
        # ----------------------------------------------------

        if interval == "1day":

            days_back = (
                request_size * 2
            )

        else:

            days_back = max(
                2,
                int(
                    request_size
                    * minutes
                    / 1440
                    * 1.8
                )
            )

        start_datetime = (
            end_datetime
            - timedelta(
                days=days_back
            )
        )

        start_date = (
            start_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        end_date = (
            end_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        values = _request(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            outputsize=MAX_PER_REQUEST,
        )

        candles = _parse_values(
            values
        )

        if not candles:

            print(
                "No more historical "
                "data returned."
            )

            break

        # ----------------------------------------------------
        # Store by datetime.
        #
        # This automatically removes duplicates
        # between overlapping historical requests.
        # ----------------------------------------------------

        for candle in candles:

            all_candles[
                candle["datetime"]
            ] = candle

        print(
            f"Received: {len(candles)} | "
            f"Unique total: "
            f"{len(all_candles)}"
        )

        if len(all_candles) >= total_candles:

            break

        # ----------------------------------------------------
        # Move backwards.
        # ----------------------------------------------------

        datetimes = []

        for candle in candles:

            try:

                dt = datetime.fromisoformat(
                    candle["datetime"]
                    .replace(
                        "Z",
                        ""
                    )
                )

                datetimes.append(
                    dt
                )

            except Exception:

                pass

        if datetimes:

            oldest = min(
                datetimes
            )

            # Move slightly before oldest
            # to prevent repeatedly requesting
            # the same period.

            end_datetime = (
                oldest
                - timedelta(
                    minutes=minutes
                )
            )

        else:

            end_datetime = (
                start_datetime
                - timedelta(
                    minutes=minutes
                )
            )

        remaining = (
            total_candles
            - len(all_candles)
        )

        request_number += 1

        # ----------------------------------------------------
        # Respect API rate limits.
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY
        )

        # Safety limit to avoid an infinite loop
        # if the provider stops returning new data.

        if request_number > 30:

            print(
                "Stopping historical "
                "download after 30 requests."
            )

            break

    candles = list(
        all_candles.values()
    )

    candles.sort(
        key=lambda x: x["datetime"]
    )

    if len(candles) > total_candles:

        candles = candles[
            -total_candles:
        ]

    print()
    print(
        "Historical download complete."
    )

    print(
        f"Requested : {total_candles}"
    )

    print(
        f"Received  : {len(candles)}"
    )

    if candles:

        print(
            f"First     : "
            f"{candles[0]['datetime']}"
        )

        print(
            f"Last      : "
            f"{candles[-1]['datetime']}"
        )

    return candles
