import requests
import pandas as pd
import time
import threading
import os
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL = "BTCUSD"
TIMEFRAME = "15m"
BASE_URL = "https://api.delta.exchange"

# ======================
# TELEGRAM
# ======================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ======================
# RSI
# ======================
def get_rsi(df):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 0.00001)
    return 100 - (100 / (1 + rs))

# ======================
# BOT
# ======================
def run_bot():
    last = None

    print("Bot started", flush=True)

    while True:
        try:
            url = f"{BASE_URL}/v2/history/candles"
            params = {"symbol": SYMBOL, "resolution": TIMEFRAME, "limit": 100}

            res = requests.get(url, params=params)
            data = res.json()["result"]

            df = pd.DataFrame(data)
            df['close'] = pd.to_numeric(df['close'])
            df = df.sort_values('time')

            df['rsi'] = get_rsi(df)

            cur = df.iloc[-2]
            prev = df.iloc[-3]

            price = cur['close']
            rsi = round(cur['rsi'], 2)
            prev_rsi = prev['rsi']

            print(f"Price: {price} | RSI: {rsi}", flush=True)

            # LONG
            if prev_rsi < 50 and rsi >= 50 and last != "LONG":
                send(f"🟢 LONG\nPrice: {price}\nRSI: {rsi}")
                last = "LONG"

            # SHORT
            elif prev_rsi > 50 and rsi <= 50 and last != "SHORT":
                send(f"🔴 SHORT\nPrice: {price}\nRSI: {rsi}")
                last = "SHORT"

        except Exception as e:
            print("Error:", e, flush=True)

        time.sleep(30)

# ======================
# FLASK
# ======================
@app.route("/")
def home():
    return "Bot running"

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
