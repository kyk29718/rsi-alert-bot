import ccxt
import pandas as pd
import requests
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================
# 🔐 TELEGRAM CONFIG (DO NOT LOG TOKEN)
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("⚠️ BOT_TOKEN or CHAT_ID missing in environment variables")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg}
        res = requests.post(url, data=payload)
        if res.status_code != 200:
            print(f"❌ Telegram Error: {res.text}")
    except Exception as e:
        print(f"📡 Telegram Exception: {e}")

# ==============================
# ⚙️ SETTINGS
# ==============================
symbol = 'BTC/USDT'
timeframe = '15m'
RSI_PERIOD = 14
TARGET_POINTS = 200

exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# ==============================
# RSI CALCULATION
# ==============================
def rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ==============================
# BOT LOOP
# ==============================
def run_bot():
    last_signal = None
    last_candle_time = None

    print("🚀 RSI Bot Started")
    send_telegram("🚀 RSI Bot Initialized - Monitoring BTC/USDT 15m")

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
            df['rsi'] = rsi(df, RSI_PERIOD)

            candle_time = df['time'].iloc[-2]
            if candle_time == last_candle_time:
                time.sleep(30)
                continue
            last_candle_time = candle_time

            prev_rsi = df['rsi'].iloc[-3]
            curr_rsi = df['rsi'].iloc[-2]
            price = df['close'].iloc[-2]
            high = df['high'].iloc[-2]
            low = df['low'].iloc[-2]

            print(f"Candle Closed | Price: {price} | RSI: {round(curr_rsi,2)}")

            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = f"🚀 LONG\nPrice: {price}\nSL: {low}\nTarget: {price + TARGET_POINTS}"
                send_telegram(msg)
                last_signal = "LONG"

            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = f"🔻 SHORT\nPrice: {price}\nSL: {high}\nTarget: {price - TARGET_POINTS}"
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(30)
        except Exception as e:
            print("Loop Error:", e)
            time.sleep(15)

# ==============================
# HEALTH CHECK SERVER
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"RSI Bot is running on port 10000")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

def keep_alive():
    port = 10000  # Hardcoded for Render
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Web Server running on port {port}")
    server.serve_forever()

# ==============================
# START BOT
# ==============================
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    run_bot()
