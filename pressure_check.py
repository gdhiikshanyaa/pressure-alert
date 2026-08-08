import requests
from datetime import datetime

# --- Config ---
LAT = 13.0827
LON = 80.2707
THRESHOLD = 5  # hPa drop that triggers alert
NTFY_TOPIC = "chennai-pressure-alert-x7k2q9"  # <-- change this to YOUR topic name

def get_pressure_data():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=surface_pressure&forecast_days=1"
    response = requests.get(url)
    data = response.json()
    return data['hourly']['surface_pressure']

def send_alert(current, three_hrs_ago, drop):
    message = (
        f"⚠️ Pressure dropped {drop:.2f} hPa in 3 hrs\n"
        f"Now: {current} hPa | 3hrs ago: {three_hrs_ago} hPa\n"
        f"Weather change likely — headache possible."
    )
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": "Pressure Alert", "Priority": "high", "Tags": "warning"}
    )

def check_pressure():
    pressures = get_pressure_data()
    current_hour = datetime.now().hour

    current = pressures[current_hour]
    three_hrs_ago = pressures[current_hour - 3]
    drop = three_hrs_ago - current

    print(f"Current pressure     : {current} hPa")
    print(f"3 hours ago          : {three_hrs_ago} hPa")
    print(f"Pressure drop        : {drop:.2f} hPa")
    print("-" * 35)

    if drop >= THRESHOLD:
        print("⚠️  ALERT — Significant pressure drop! Sending notification...")
        send_alert(current, three_hrs_ago, drop)
    else:
        print("✅  Pressure stable. No alert needed.")

check_pressure()
