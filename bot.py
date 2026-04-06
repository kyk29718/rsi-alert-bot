import websocket
import json
import pandas as pd
import numpy as np
import threading
import time
import os
import requests
from flask import Flask

# ==============================
# 🔐 CONFIG
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL = "BTCUSDTPERP"
RSI_PERIOD = 14

app = Flask(__name__)

# ==============================
# 📩 TELEGRAM
# ==============================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )

        if not res.json().get("ok"):
            print("Telegram Error:", res.text)

    except Exception as e:
        print("Telegram Exception:", e)

# ==============================
# 📊 RSI
# ==============================
def calculate_rsi(prices, period=14):
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, 0.00001)
    rsi = 100 - (100 / (1 + rs))

    return rsi

# ==============================
# 🤖 BOT LOGIC
# ==============================
price_data = []
last_signal = None

def on_message(ws, message):
    global price_data, last_signal

    try:
        msg = json.loads(message)

        if msg.get("type") == "trade":
            for trade in msg.get("data", []):
                price = float(trade["price"])
                price_data.append(price)

                if len(price_data) > 100:
                    price_data = price_data[-100:]

                if len(price_data) >= RSI_PERIOD:
                    rsi_series = calculate_rsi(price_data, RSI_PERIOD)

                    if len(rsi_series.dropna()) < 2:
                        return

                    curr_rsi = round(rsi_series.iloc[-1], 2)
                    prev_rsi = round(rsi_series.iloc[-2], 2)

                    print(f"Price: {price} | RSI: {curr_rsi}")

                    if prev_rsi < 50 <= curr_rsi and last_signal != "LONG":
                        send_telegram(f"🟢 LONG SIGNAL\nPrice: {price}\nRSI: {curr_rsi}")
                        last_signal = "LONG"

                    elif prev_rsi > 50 >= curr_rsi and last_signal != "SHORT":
                        send_telegram(f"🔴 SHORT SIGNAL\nPrice: {price}\nRSI: {curr_rsi}")
                        last_signal = "SHORT"

    except Exception as e:
        print("Message Error:", e)

def on_open(ws):
    print("✅ WebSocket Connected")

    subscribe_msg = {
        "type": "subscribe",
        "payload": {
            "channels": [
                {
                    "name": "trades",
                    "symbols": [SYMBOL]
                }
            ]
        }
    }

    ws.send(json.dumps(subscribe_msg))

def on_error(ws, error):
    print("WebSocket Error:", error)

def on_close(ws, code, msg):
    print("WebSocket Closed:", code, msg)

# ==============================
# 🔄 AUTO RECONNECT
# ==============================
def start_bot():
    ws_url = "wss://api.delta.exchange/v2/ws"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.delta.exchange"
    }

    while True:
        try:
            ws = websocket.WebSocketApp(
                ws_url,
                header=[f"{k}: {v}" for k, v in headers.items()],
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever()

        except Exception as e:
            print("Reconnect Error:", e)

        print("🔄 Reconnecting in 5s...")
        time.sleep(5)

# ==============================
# 🌐 FLASK ROUTES
# ==============================
@app.route("/")
def home():
    return "Bot is running 🚀"

@app.route("/health")
def health():
    return {"status": "ok"}

# ==============================
# ▶️ MAIN
# ==============================
if __name__ == "__main__":
    print("🚀 Bot starting...")

    threading.Thread(target=start_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
