import websocket
import json
import pandas as pd
import numpy as np
import threading
import time
import os
import requests

# ==============================
# 🔐 CONFIGURATION
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL = "BTCUSDTPERP"   # Correct Delta symbol
RSI_PERIOD = 14

# ==============================
# 📩 TELEGRAM FUNCTION
# ==============================
def send_telegram(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("Missing BOT_TOKEN or CHAT_ID")
            return

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )

        response = res.json()
        if not response.get("ok"):
            print("Telegram Error:", response)

    except Exception as e:
        print("Telegram Exception:", e)

# ==============================
# 📊 RSI CALCULATION
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
# 🔁 BOT LOGIC
# ==============================
price_data = []
last_signal = None

def on_message(ws, message):
    global price_data, last_signal

    try:
        msg = json.loads(message)

        # DEBUG (optional)
        # print(msg)

        if msg.get("type") == "trade":
            for trade in msg.get("data", []):
                price = float(trade["price"])
                price_data.append(price)

                # Keep last 100 prices
                if len(price_data) > 100:
                    price_data = price_data[-100:]

                if len(price_data) >= RSI_PERIOD:
                    rsi_series = calculate_rsi(price_data, RSI_PERIOD)

                    if len(rsi_series.dropna()) < 2:
                        return

                    curr_rsi = round(rsi_series.iloc[-1], 2)
                    prev_rsi = round(rsi_series.iloc[-2], 2)

                    print(f"Price: {price} | RSI: {curr_rsi}")

                    # LONG signal
                    if prev_rsi < 50 <= curr_rsi and last_signal != "LONG":
                        send_telegram(f"🟢 LONG SIGNAL\nPrice: {price}\nRSI: {curr_rsi}")
                        last_signal = "LONG"

                    # SHORT signal
                    elif prev_rsi > 50 >= curr_rsi and last_signal != "SHORT":
                        send_telegram(f"🔴 SHORT SIGNAL\nPrice: {price}\nRSI: {curr_rsi}")
                        last_signal = "SHORT"

    except Exception as e:
        print("Message Error:", e)


def on_error(ws, error):
    print("WebSocket Error:", error)


def on_close(ws, close_status_code, close_msg):
    print("WebSocket Closed:", close_status_code, close_msg)


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


# ==============================
# 🌐 START BOT
# ==============================
def start_bot():
    ws_url = "wss://api.delta.exchange/v2/ws"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.delta.exchange"
    }

    ws = websocket.WebSocketApp(
        ws_url,
        header=[f"{k}: {v}" for k, v in headers.items()],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()


# ==============================
# ▶️ MAIN
# ==============================
if __name__ == "__main__":
    print("🚀 Delta RSI Bot Running...")

    threading.Thread(target=start_bot, daemon=True).start()

    # Keep main thread alive
    while True:
        time.sleep(10)
