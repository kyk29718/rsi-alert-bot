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

SYMBOL = "BTCUSD"  # BTC/USD perpetual futures
RSI_PERIOD = 14

# ==============================
# 📩 TELEGRAM FUNCTION
# ==============================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        if res.status_code != 200:
            print("Telegram Error:", res.text)
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
        if 'type' in msg and msg['type'] == 'trade' and msg['symbol'] == SYMBOL:
            price = float(msg['price'])
            price_data.append(price)

            # Keep last 100 prices
            if len(price_data) > 100:
                price_data = price_data[-100:]

            if len(price_data) >= RSI_PERIOD:
                rsi_series = calculate_rsi(price_data, RSI_PERIOD)
                curr_rsi = round(rsi_series.iloc[-1], 2)
                prev_rsi = round(rsi_series.iloc[-2], 2)

                # LONG signal
                if prev_rsi < 50 <= curr_rsi and last_signal != "LONG":
                    send_telegram(f"🟢 LONG SIGNAL\nPrice: {price}\nRSI: {curr_rsi}")
                    last_signal = "LONG"

                # SHORT signal
                elif prev_rsi > 50 >= curr_rsi and last_signal != "SHORT":
                    send_telegram(f"🔴 SHORT SIGNAL\nPrice: {price}\nRSI: {curr_rsi}")
                    last_signal = "SHORT"

    except Exception as e:
        print("WebSocket Message Error:", e)

def on_error(ws, error):
    print("WebSocket Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket Closed:", close_status_code, close_msg)

def on_open(ws):
    print("WebSocket Connection Opened")
    # Subscribe to BTCUSD trades
    subscribe_msg = {
        "type": "subscribe",
        "channels": [
            {"name": "trades", "symbols": [SYMBOL]}
        ]
    }
    ws.send(json.dumps(subscribe_msg))

# ==============================
# 🌐 RUN BOT
# ==============================
def start_bot():
    ws_url = "wss://api.delta.exchange/v2/ws"
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    print("🚀 Delta RSI Bot Running...")
