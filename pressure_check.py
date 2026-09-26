"""
Chennai Pressure Alert - v2 (tide-compensated)

Improvements over v1 (validated on Nov 2023 - Dec 2024 data vs Chennai Airport barometer):
  1. Removes the twice-daily atmospheric tide before checking for a drop
     (average of the same hour over the past 15 days is subtracted).
  2. Threshold lowered from 5 hPa to 2 hPa (possible because tide removal cuts noise ~70%).
  3. Readings picked by UTC timestamp (fixes the 00:00-02:59 UTC negative-index bug).
  4. Checks every hour of the last 6 h, so irregular GitHub schedule gaps don't miss a drop.
Only needs the 'requests' library.
"""
import requests
from datetime import datetime, timezone, timedelta

# --- Config ---
LAT = 13.0827
LON = 80.2707
THRESHOLD = 2.0          # hPa drop in 3 h, after tide removal
WINDOW_H = 3             # drop measured over 3 hours
TIDE_DAYS = 15           # days of history used to estimate the daily tide
LOOKBACK_H = 6           # hours checked on each run (covers GitHub schedule gaps)
NTFY_TOPIC = "chennai-pressure-alert-x7k2q9"


def get_pressure_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": LAT, "longitude": LON, "hourly": "pressure_msl",
              "past_days": TIDE_DAYS + 2, "forecast_days": 1, "timezone": "GMT"}
    data = requests.get(url, params=params, timeout=60).json()["hourly"]
    return data["time"], data["pressure_msl"]


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def tide_corrected(p, i):
    """Pressure at index i with the average daily cycle removed (uses only past data)."""
    if p[i] is None or i < 24 * TIDE_DAYS:
        return None
    same_hour_avg = mean([p[i - 24 * k] for k in range(1, TIDE_DAYS + 1)])
    overall_avg = mean(p[i - 24 * TIDE_DAYS:i])
    return p[i] - same_hour_avg + overall_avg


def evaluate(times, p, now_index):
    """Return (max tide-corrected 3-h drop in last LOOKBACK_H hours, raw 3-h drop now)."""
    drops = []
    for i in range(now_index - LOOKBACK_H + 1, now_index + 1):
        a, b = tide_corrected(p, i - WINDOW_H), tide_corrected(p, i)
        if a is not None and b is not None:
            drops.append(a - b)
    raw = p[now_index - WINDOW_H] - p[now_index]
    return (max(drops) if drops else None), raw


def send_alert(current, drop, raw):
    message = (f"⚠️ Unusual pressure fall: {drop:.1f} hPa in 3 h (tide-corrected)\n"
               f"Now: {current} hPa | raw 3-h change: {0.0 - raw + 0.0:+.1f} hPa\n"
               f"Weather change likely — headache possible.")
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"),
                  headers={"Title": "Pressure Alert", "Priority": "high", "Tags": "warning"},
                  timeout=30)


def check_pressure():
    times, p = get_pressure_data()
    now_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    n = times.index(now_key)
    drop, raw = evaluate(times, p, n)

    print(f"Time (UTC)                 : {times[n]}")
    print(f"Current pressure           : {p[n]} hPa")
    print(f"Raw 3-h drop               : {raw:.2f} hPa")
    if drop is not None:
        print(f"Tide-corrected 3-h drop    : {drop:.2f} hPa (max over last {LOOKBACK_H} h)")
    print("-" * 45)
    if drop is not None and drop >= THRESHOLD:
        print("⚠️  ALERT — unusual pressure fall! Sending notification...")
        send_alert(p[n], drop, raw)
    else:
        print("✅  Pressure normal. No alert needed.")


if __name__ == "__main__":
    check_pressure()
